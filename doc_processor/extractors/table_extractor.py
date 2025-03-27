"""
表格提取器模块
"""

import gc
import re
from typing import Any, Dict, List, Optional, Set, Tuple, cast

from docx.document import Document as DocxDocument
from docx.table import Table as DocxTable
from lxml import etree

from doc_processor.exceptions import ExtractionError
from doc_processor.extractors.base import BaseExtractor
from doc_processor.models import CarInfo, CarInfoCollection
from doc_processor.utils import clean_text, process_car_info, validate_car_info

# 预编译正则表达式
WHITESPACE_PATTERN = re.compile(r"\s+")


def get_table_type(
    headers: List[str], current_category: Optional[str], current_type: Optional[str]
) -> Tuple[str, str]:
    """
    根据表头判断表格类型

    Args:
        headers: 表头列表
        current_category: 当前分类
        current_type: 当前类型

    Returns:
        分类和类型元组

    Raises:
        ValueError: 表格缺少必要的列
    """
    # 标准化表头
    normalized_headers = [h.strip().lower() for h in headers]

    # 验证必要的列是否存在
    required_columns = {"序号", "企业名称"}
    missing_columns = required_columns - set(normalized_headers)
    if missing_columns:
        raise ValueError(f"表格缺少必要的列: {missing_columns}")

    # 处理特殊的表头组合
    if "型式" in normalized_headers and "档位数" in normalized_headers:
        # 合并为变速器列
        idx = normalized_headers.index("型式")
        normalized_headers[idx] = "变速器"
        normalized_headers.pop(normalized_headers.index("档位数"))

    header_set: Set[str] = set(normalized_headers)

    # 判断表格类型
    if "排量(ml)" in header_set and "综合燃料消耗量" in header_set:
        return "节能型", "（一）乘用车"
    elif "总电量" in header_set or "电池容量" in header_set:
        return "新能源", "（一）纯电动乘用车"
    elif "能量密度" in header_set or "纯电动续驶里程" in header_set:
        return "新能源", "（二）插电式混合动力乘用车"

    # 如果无法确定类型，使用当前上下文
    return current_category or "未知", current_type or "未知"


class TableExtractor(BaseExtractor[CarInfoCollection]):
    """
    表格提取器

    Attributes:
        table: 表格对象
        table_index: 表格索引
        batch_number: 批次号
        current_category: 当前分类
        current_type: 当前类型
        chunk_size: 分块大小
    """

    def __init__(
        self,
        table: DocxTable,
        table_index: int,
        batch_number: Optional[str] = None,
        current_category: Optional[str] = None,
        current_type: Optional[str] = None,
        chunk_size: int = 1000,
        verbose: bool = False,
    ) -> None:
        """
        初始化表格提取器

        Args:
            table: 表格对象
            table_index: 表格索引
            batch_number: 批次号
            current_category: 当前分类
            current_type: 当前类型
            chunk_size: 分块大小
            verbose: 是否显示详细信息
        """
        super().__init__(f"表格提取器-{table_index + 1}", verbose)
        self.table = table
        self.table_index = table_index
        self.batch_number = batch_number
        self.current_category = current_category
        self.current_type = current_type
        self.chunk_size = chunk_size

    def extract(self) -> CarInfoCollection:
        """
        提取表格中的车辆信息

        Returns:
            车辆信息集合

        Raises:
            ExtractionError: 提取失败
        """
        try:
            # 记录开始提取表格
            self.log_info(f"开始提取表格 {self.table_index + 1}")

            # 提取所有单元格内容
            with self as extractor:
                all_rows = self._extract_table_cells_fast()
                extractor.log_step("提取单元格内容")

                if not all_rows:
                    self.log_warning(f"表格 {self.table_index + 1} 不包含有效数据")
                    return CarInfoCollection()

                # 获取并处理表头
                headers = [clean_text(cell) for cell in all_rows[0] if cell]
                if not headers:
                    self.log_warning(f"表格 {self.table_index + 1} 没有表头")
                    return CarInfoCollection()

                # 根据表头判断表格类型
                try:
                    table_category, table_type = get_table_type(
                        headers, self.current_category, self.current_type
                    )
                    self.log_info(f"表格类型: {table_category} - {table_type}")
                except ValueError as e:
                    self.log_error(f"表格类型判断失败: {str(e)}")
                    return CarInfoCollection()

                extractor.log_step("判断表格类型")

                # 创建车辆信息集合
                car_collection = CarInfoCollection()

                # 创建基础信息
                base_info = {
                    "category": table_category,
                    "sub_type": table_type,
                    "car_type": 2 if table_category == "节能型" else 1,
                    "batch": self.batch_number,
                    "table_id": self.table_index + 1,
                }

                # 处理数据行
                total_rows = len(all_rows) - 1
                valid_rows = 0
                invalid_rows = 0

                # 分块处理
                for chunk_start in range(1, len(all_rows), self.chunk_size):
                    chunk_end = min(chunk_start + self.chunk_size, len(all_rows))
                    chunk_rows = all_rows[chunk_start:chunk_end]

                    for row_idx, cells in enumerate(chunk_rows, chunk_start):
                        # 跳过空行
                        if not any(str(cell).strip() for cell in cells):
                            continue

                        # 处理列数不匹配的情况
                        if len(cells) != len(headers):
                            # 调整单元格数量以匹配表头
                            if len(cells) > len(headers):
                                cells = cells[: len(headers)]
                            else:
                                cells.extend([""] * (len(headers) - len(cells)))

                        # 创建车辆信息字典
                        car_info = base_info.copy()
                        car_info["raw_text"] = " | ".join(str(cell) for cell in cells)

                        # 将表头与单元格内容映射
                        for header, value in zip(headers, cells):
                            if header:  # 忽略空表头
                                car_info[header] = clean_text(str(value))

                        # 处理车辆信息
                        car_info = process_car_info(car_info, self.batch_number)

                        # 验证车辆信息
                        is_valid, error_msg, fixed_info = validate_car_info(car_info)

                        if is_valid and fixed_info:
                            car_collection.add_from_dict(fixed_info)
                            valid_rows += 1
                        else:
                            invalid_rows += 1
                            if self.verbose:
                                self.log_info(f"行 {row_idx} 无效: {error_msg}")

                    # 主动触发垃圾回收
                    if len(car_collection.cars) > 5000:
                        gc.collect()

                extractor.log_step("处理数据行")

                # 记录提取结果
                self.log_info(
                    f"表格 {self.table_index + 1} 提取完成："
                    f"总行数 {total_rows}，有效行 {valid_rows}，无效行 {invalid_rows}"
                )

                return car_collection

        except Exception as e:
            raise ExtractionError(
                f"提取表格 {self.table_index + 1} 失败: {str(e)}", element_type="table"
            )

    def _extract_table_cells_fast(self) -> List[List[str]]:
        """
        优化的表格提取方法

        Returns:
            表格单元格内容列表
        """
        try:
            rows = []
            header_processed = False
            last_company = ""
            last_brand = ""

            # 使用lxml的xpath直接提取文本
            for row in self.table._tbl.xpath(".//w:tr"):
                cells = []
                for cell in row.xpath(".//w:tc"):
                    # 直接获取所有文本节点
                    text = "".join(t.text or "" for t in cell.xpath(".//w:t"))
                    cells.append(text.strip())

                if not header_processed:
                    processed_headers = self._process_merged_headers(cells)
                    rows.append(processed_headers)
                    header_processed = True
                    continue

                processed_row = self._process_data_row(cells, last_company, last_brand)
                if processed_row:
                    if processed_row[1]:  # 企业名称
                        last_company = processed_row[1]
                    if processed_row[2]:  # 品牌
                        last_brand = processed_row[2]
                    rows.append(processed_row)

            return rows
        except Exception as e:
            self.log_error(f"表格提取错误: {str(e)}")
            return []

    def _process_merged_headers(self, headers: List[str]) -> List[str]:
        """
        处理合并的表头，例如将'型式'和'档位数'合并为'变速器'

        Args:
            headers: 原始表头列表

        Returns:
            处理后的表头列表
        """
        processed = []
        i = 0
        while i < len(headers):
            if (
                i + 1 < len(headers)
                and headers[i] == "型式"
                and headers[i + 1] == "档位数"
            ):
                processed.append("变速器")
                i += 2
            else:
                processed.append(headers[i])
                i += 1
        return processed

    def _process_data_row(
        self, row: List[str], last_company: str, last_brand: str
    ) -> Optional[List[str]]:
        """
        处理数据行，包括空值处理和数据继承

        Args:
            row: 原始数据行
            last_company: 上一个有效企业名称
            last_brand: 上一个有效品牌

        Returns:
            处理后的数据行，如果是无效行则返回None
        """
        # 跳过全空行
        if not any(cell.strip() for cell in row):
            return None

        # 处理合计行
        if any(cell.strip().startswith(("合计", "总计")) for cell in row):
            return None

        processed = []
        for i, cell in enumerate(row):
            value = cell.strip()
            if i == 1 and not value:  # 企业名称为空
                processed.append(last_company)
            elif i == 2 and not value:  # 品牌/通用名称为空
                processed.append(last_brand)
            else:
                processed.append(value)

        return processed
