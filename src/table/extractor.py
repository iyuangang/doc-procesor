"""
表格提取器模块 - 从文档表格中提取数据
"""

import gc
import logging
from typing import Dict, Any, List, Optional, Tuple

from docx.table import Table

from ..utils.text_processing import clean_text


class TableExtractor:
    """表格数据提取器，用于从文档表格中提取数据"""

    def __init__(self, chunk_size: int = 1000):
        """
        初始化表格提取器

        Args:
            chunk_size: 处理数据的分块大小
        """
        self.logger = logging.getLogger(__name__)
        self._chunk_size = chunk_size
        self._table_cache: Dict[int, List[Dict[str, Any]]] = {}

    def extract_table_cells_fast(self, table: Table) -> List[List[str]]:
        """
        优化的表格提取方法

        Args:
            table: 文档表格对象

        Returns:
            包含表格单元格内容的二维列表
        """
        try:
            rows = []
            header_processed = False
            last_company = ""
            last_brand = ""

            # 尝试使用lxml的xpath直接提取文本
            for row in table._tbl.xpath(".//w:tr"):
                cells = []
                for cell in row.xpath(".//w:tc"):
                    # 直接获取所有文本节点
                    text = "".join(t.text for t in cell.xpath(".//w:t"))
                    cells.append(text.strip())

                if not header_processed:
                    processed_headers = self._process_merged_headers(cells)
                    rows.append(processed_headers)
                    header_processed = True
                    continue

                processed_row = self._process_data_row(cells, last_company, last_brand)
                if processed_row:
                    if processed_row[1]:
                        last_company = processed_row[1]
                    if processed_row[2]:
                        last_brand = processed_row[2]
                    rows.append(processed_row)

            return rows
        except Exception as e:
            self.logger.error(f"表格提取错误: {str(e)}")
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
            row: 行数据列表
            last_company: 上一行的企业名称
            last_brand: 上一行的品牌名称

        Returns:
            处理后的行数据，如果是空行或合计行则返回None
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

    def extract_car_info(
        self,
        table: Table,
        table_index: int,
        category: str,
        sub_type: str,
        batch_number: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        从表格中提取车辆信息

        Args:
            table: 文档表格对象
            table_index: 表格索引
            category: 车辆类别
            sub_type: 车辆子类型
            batch_number: 批次号

        Returns:
            车辆信息字典列表
        """
        # 检查缓存
        if table_index in self._table_cache:
            return self._table_cache[table_index]

        table_cars: List[Dict[str, Any]] = []
        if not table or not table.rows:
            return table_cars

        # 使用快速方法提取所有单元格内容
        all_rows = self.extract_table_cells_fast(table)
        if not all_rows:
            return table_cars

        # 获取并处理表头
        headers = [clean_text(cell) for cell in all_rows[0] if cell]
        if not headers:
            return table_cars

        # 预先创建基础信息
        base_info = {
            "category": category,
            "sub_type": sub_type,
            "energytype": 2 if category == "节能型" else 1,
            "batch": batch_number,
            "table_id": table_index + 1,  # 添加表格ID，从1开始计数
        }

        total_rows = len(all_rows) - 1

        # 分块处理数据行
        for chunk_start in range(1, len(all_rows), self._chunk_size):
            chunk_end = min(chunk_start + self._chunk_size, len(all_rows))
            chunk_rows = all_rows[chunk_start:chunk_end]

            # 批量处理当前块的数据行
            for row_idx, cells in enumerate(chunk_rows, chunk_start):
                # 跳过空行
                if not any(str(cell).strip() for cell in cells):
                    continue

                # 记录列数不匹配的情况，但仍然处理数据
                if len(cells) != len(headers):
                    self.logger.warning(
                        f"表格 {table_index + 1} 第 {row_idx} 行列数不匹配: "
                        f"预期 {len(headers)} 列，实际 {len(cells)} 列"
                    )

                    # 调整单元格数量以匹配表头
                    if len(cells) > len(headers):
                        cells = cells[: len(headers)]
                    else:
                        cells.extend([""] * (len(headers) - len(cells)))

                # 创建新的字典，避免引用同一个对象
                car_info = base_info.copy()
                car_info["raw_text"] = " | ".join(str(cell) for cell in cells)

                # 使用zip优化字段映射，同时清理文本
                car_info.update(
                    {
                        header: clean_text(str(value))
                        for header, value in zip(headers, cells)
                    }
                )

                # 处理车辆信息 (这里我们应该调用外部的process_car_info函数)
                # 从..utils.validation导入process_car_info
                from ..utils.validation import process_car_info

                car_info = process_car_info(car_info, batch_number)
                table_cars.append(car_info)

            # 主动触发垃圾回收
            if len(table_cars) > 5000:
                gc.collect()

        # 缓存结果
        self._table_cache[table_index] = table_cars

        self.logger.info(
            f"表格 {table_index + 1} 处理了 {total_rows} 行，提取数据 {len(table_cars)} 行"
        )

        return table_cars

    def clear_cache(self) -> None:
        """清除缓存"""
        self._table_cache.clear()
        gc.collect()
