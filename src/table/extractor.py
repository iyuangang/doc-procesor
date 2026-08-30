"""
表格提取器模块 - 从文档表格中提取数据
"""

import logging
from typing import Dict, Any, Iterable, Iterator, List, Optional

from docx.table import Table

from ..utils.text_processing import clean_text
from ..utils.validation import process_car_info, validate_car_info


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
        self._table_metrics: Dict[int, Dict[str, int]] = {}

    def extract_table_cells_fast(self, table: Table) -> List[List[str]]:
        """
        优化的表格提取方法

        Args:
            table: 文档表格对象

        Returns:
            包含表格单元格内容的二维列表
        """
        return list(self.iter_table_rows(table))

    def iter_table_rows(self, table: Table) -> Iterator[List[str]]:
        """Yield normalized table rows without materializing the whole matrix."""
        try:

            def raw_rows() -> Iterator[List[str]]:
                for row in table._tbl.xpath(".//w:tr"):
                    cells = []
                    for cell in row.xpath(".//w:tc"):
                        text = "".join(t.text for t in cell.xpath(".//w:t"))
                        cells.append(text.strip())
                    yield cells

            yield from self._normalize_rows(raw_rows())
        except Exception as e:
            self.logger.error(f"表格提取错误: {str(e)}")
            raise RuntimeError(f"无法读取表格内容: {e}") from e

    def _normalize_rows(self, raw_rows: Iterable[List[str]]) -> Iterator[List[str]]:
        header_processed = False
        last_company = ""
        last_brand = ""
        expected_columns = 0
        company_index: Optional[int] = None
        brand_index: Optional[int] = None

        for cells in raw_rows:
            if not header_processed:
                expected_columns = len(cells)
                normalized = [clean_text(value) for value in cells]
                company_index = next(
                    (
                        index
                        for index, value in enumerate(normalized)
                        if value in {"企业名称", "生产企业", "企业"}
                    ),
                    None,
                )
                brand_index = next(
                    (
                        index
                        for index, value in enumerate(normalized)
                        if value in {"品牌", "商标", "通用名称"}
                    ),
                    None,
                )
                header_processed = True
                yield cells
                continue

            if len(cells) > expected_columns and expected_columns > 0:
                cells = cells[: expected_columns - 1] + [
                    " ".join(cells[expected_columns - 1 :])
                ]
            elif len(cells) < expected_columns:
                cells.extend([""] * (expected_columns - len(cells)))

            processed_row = self._process_data_row(
                cells,
                last_company,
                last_brand,
                company_index=company_index,
                brand_index=brand_index,
            )
            if processed_row is None:
                continue
            if company_index is not None and processed_row[company_index]:
                last_company = processed_row[company_index]
            if brand_index is not None and processed_row[brand_index]:
                last_brand = processed_row[brand_index]
            yield processed_row

    def _process_merged_headers(self, headers: List[str]) -> List[str]:
        """
        处理合并的表头，识别并合并相关列

        Args:
            headers: 原始表头列表

        Returns:
            处理后的表头列表
        """
        processed = []
        i = 0

        # 标准化表头，移除空格并转为小写
        normalized_headers = [h.strip().lower() for h in headers]

        while i < len(headers):
            # 处理变速器相关列
            if (
                i + 1 < len(headers)
                and normalized_headers[i] == "型式"
                and normalized_headers[i + 1] == "档位数"
            ):
                processed.append("变速器")
                i += 2
            # 处理发动机相关列
            elif (
                i + 1 < len(headers)
                and normalized_headers[i].startswith("发动")
                and normalized_headers[i + 1].startswith("排量")
            ):
                processed.append("发动机")
                i += 2
            # 处理其他可能的合并列
            elif (
                i + 1 < len(headers)
                and normalized_headers[i] == "企业"
                and normalized_headers[i + 1] == "名称"
            ):
                processed.append("企业名称")
                i += 2
            # 处理注释或备注列
            elif any(kw in normalized_headers[i] for kw in ["注", "备注", "说明"]):
                processed.append("备注")
                i += 1
            # 处理其他列
            else:
                processed.append(headers[i])
                i += 1

        return processed

    def _process_data_row(
        self,
        row: List[str],
        last_company: str,
        last_brand: str,
        company_index: Optional[int] = 1,
        brand_index: Optional[int] = 2,
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
            if company_index is not None and i == company_index and not value:
                processed.append(last_company)
            elif brand_index is not None and i == brand_index and not value:
                processed.append(last_brand)
            else:
                processed.append(value)

        return processed

    def extract_car_info(
        self,
        table: Table,
        table_index: int,
        category: Optional[str],
        sub_type: Optional[str],
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
        if table_index in self._table_cache:
            return self._table_cache[table_index]
        if not table or not table.rows:
            return []

        return self._extract_car_info_rows(
            self.iter_table_rows(table),
            table_index,
            category,
            sub_type,
            batch_number,
        )

    def extract_car_info_rows(
        self,
        raw_rows: Iterable[List[str]],
        table_index: int,
        category: Optional[str],
        sub_type: Optional[str],
        batch_number: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Extract records from a one-pass raw-row source."""
        if table_index in self._table_cache:
            return self._table_cache[table_index]
        return self._extract_car_info_rows(
            self._normalize_rows(raw_rows),
            table_index,
            category,
            sub_type,
            batch_number,
        )

    def _extract_car_info_rows(
        self,
        row_iterator: Iterator[List[str]],
        table_index: int,
        category: Optional[str],
        sub_type: Optional[str],
        batch_number: Optional[str],
    ) -> List[Dict[str, Any]]:
        table_cars: List[Dict[str, Any]] = []

        try:
            header_row = next(row_iterator)
        except StopIteration:
            return table_cars

        # 获取并处理表头
        headers = [
            clean_text(cell) or f"未命名列_{index + 1}"
            for index, cell in enumerate(header_row)
        ]
        if not headers:
            return table_cars

        # 预先创建基础信息
        normalized_category = category or "未知"
        base_info = {
            "category": normalized_category,
            "sub_type": sub_type or "未知",
            "energytype": {"新能源": 1, "节能型": 2}.get(normalized_category),
            "batch": batch_number,
            "table_id": table_index + 1,  # 添加表格ID，从1开始计数
        }

        total_rows = 0
        for row_idx, cells in enumerate(row_iterator, 1):
            total_rows += 1
            if not any(str(cell).strip() for cell in cells):
                continue

            if len(cells) != len(headers):
                self.logger.debug(
                    "表格 %d 第 %d 行列数不一致: 表头 %d，数据 %d",
                    table_index + 1,
                    row_idx,
                    len(headers),
                    len(cells),
                )

            car_info = base_info.copy()
            car_info["raw_text"] = " | ".join(str(cell) for cell in cells)
            car_info.update(
                {
                    header: clean_text(str(value))
                    for header, value in zip(headers, cells)
                }
            )

            car_info = process_car_info(car_info, batch_number)
            is_valid, reason, validated = validate_car_info(car_info)
            if is_valid and validated is not None:
                table_cars.append(validated)
            else:
                self.logger.debug(
                    "跳过表格 %d 第 %d 行: %s",
                    table_index + 1,
                    row_idx,
                    reason,
                )

            if total_rows % self._chunk_size == 0:
                self.logger.debug(
                    "表格 %d 已流式处理 %d 行", table_index + 1, total_rows
                )

        # 缓存结果
        self._table_cache[table_index] = table_cars
        self._table_metrics[table_index + 1] = {
            "candidate_count": total_rows,
            "valid_count": len(table_cars),
            "invalid_count": total_rows - len(table_cars),
        }

        self.logger.info(
            f"表格 {table_index + 1} 处理了 {total_rows} 行，提取数据 {len(table_cars)} 行"
        )

        return table_cars

    def clear_cache(self) -> None:
        """清除缓存"""
        self._table_cache.clear()
        self._table_metrics.clear()

    def get_metrics(self) -> Dict[int, Dict[str, int]]:
        """Return a copy of per-table candidate and validation counts."""
        return {
            table_id: values.copy() for table_id, values in self._table_metrics.items()
        }
