"""
文档处理器模块 - 提供文档处理的核心功能
"""

import gc
import logging
import os
import time
from collections import deque
from typing import Dict, Any, Optional, List
from zipfile import ZipFile

import psutil
from docx import Document
from docx.document import Document as DocxDocument

from ..batch.validator import verify_batch_consistency, verify_all_batches
from ..config.settings import settings
from ..document.parser import (
    extract_declared_count,
    extract_declared_count_from_rows,
    extract_declared_count_from_text,
)
from ..document.streaming import iter_document_blocks
from ..models.document_node import DocumentNode, DocumentStructure
from ..table.extractor import TableExtractor
from ..utils.chinese_numbers import extract_batch_number
from ..utils.csv_output import write_csv_atomic


class ProcessingError(Exception):
    """处理错误异常"""

    pass


class DocumentError(Exception):
    """文档错误异常"""

    pass


class DocProcessor:
    """文档处理器类，用于处理Word文档中的车辆信息"""

    def __init__(
        self,
        doc_path: str,
        verbose: bool = True,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化文档处理器

        Args:
            doc_path: 文档路径
            verbose: 是否显示详细信息
            config: 配置信息
        """
        self.doc_path = doc_path
        self.start_time = time.time()
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.doc_structure = DocumentStructure()
        self.doc: Optional[DocxDocument] = None

        self.current_category: Optional[str] = None
        self.current_type: Optional[str] = None
        self.batch_number: Optional[str] = None
        self.cars: List[Dict[str, Any]] = []
        self._processing_times: Dict[str, float] = {}
        self.declared_count: Optional[int] = None  # 声明的总记录数
        self.consistency_result: Dict[str, Any] = {}
        self.batch_results: Dict[str, Any] = {}
        self.candidate_record_count = 0
        self.invalid_record_count = 0

        # 从配置加载设置
        self._chunk_size = self._get_config("performance.chunk_size", 1000)
        if not isinstance(self._chunk_size, int) or self._chunk_size <= 0:
            raise DocumentError("performance.chunk_size 必须是大于 0 的整数")
        self.verbose = verbose
        # 添加跳过总记录数检查的配置选项
        self._skip_count_check = self._get_config("document.skip_count_check", False)
        self._skip_verification = self._get_config("document.skip_verification", False)
        # 设置搜索限制
        self._max_paragraphs_to_search = self._get_config(
            "document.max_paragraphs_to_search", 30
        )
        self._max_tables_to_search = self._get_config(
            "document.max_tables_to_search", 5
        )
        self._build_structure = self._get_config("document.build_structure", verbose)

        self.file_size = self._get_file_size()
        self._streaming_xml = self._should_stream_document()

        self.logger.info(f"初始化文档处理器: {doc_path}")

        self.current_section: Optional[DocumentNode] = None
        self.current_subsection: Optional[DocumentNode] = None
        self.current_numbered_section: Optional[DocumentNode] = (
            None  # 用于跟踪带数字编号的节点
        )

        # 初始化表格提取器
        self.table_extractor = TableExtractor(chunk_size=self._chunk_size)

        try:
            self._load_document()
        except Exception as e:
            self.logger.error(f"初始化文档处理器失败: {str(e)}")
            raise DocumentError(f"无法加载文档 {doc_path}: {str(e)}")

    def _get_config(self, key: str, default: Any) -> Any:
        """
        获取配置值

        Args:
            key: 配置键，使用点号分隔，例如 'performance.chunk_size'
            default: 默认值

        Returns:
            配置值
        """
        if self.config:
            # 处理嵌套键
            if "." in key:
                parts = key.split(".")
                value = self.config
                for part in parts:
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        return default
                return value
            return self.config.get(key, default)

        # 如果没有提供配置，尝试从全局设置获取
        try:
            return settings.get(key, default)
        except (AttributeError, TypeError):
            return default

    def _get_file_size(self) -> int:
        """Return the source size while preserving the public error contract."""
        try:
            return os.path.getsize(self.doc_path)
        except OSError as exc:
            raise DocumentError(f"无法访问文档 {self.doc_path}: {exc}") from exc

    def _should_stream_document(self) -> bool:
        """Resolve the configured parser mode for this document."""
        mode = self._get_config("performance.streaming_xml", "auto")
        if isinstance(mode, str):
            normalized = mode.strip().lower()
            if normalized in {"true", "yes", "on", "1"}:
                return True
            if normalized in {"false", "no", "off", "0"}:
                return False
            if normalized != "auto":
                raise DocumentError(
                    "performance.streaming_xml 必须是 auto、true 或 false"
                )
        elif isinstance(mode, bool):
            return mode
        else:
            raise DocumentError("performance.streaming_xml 必须是 auto、true 或 false")

        threshold_mb = self._get_config("performance.streaming_threshold_mb", 1)
        try:
            threshold_bytes = max(float(threshold_mb), 0) * 1024 * 1024
        except (TypeError, ValueError) as exc:
            raise DocumentError(
                "performance.streaming_threshold_mb 必须是非负数"
            ) from exc
        return self.file_size >= threshold_bytes

    def _load_document(self) -> None:
        """
        安全加载文档，处理大文件

        Raises:
            DocumentError: 无法加载文档
        """
        try:
            self.logger.info(
                "加载文档 %s, 大小: %.2fMB, 解析模式: %s",
                self.doc_path,
                self.file_size / 1024 / 1024,
                "OOXML 流式" if self._streaming_xml else "python-docx",
            )

            if self._streaming_xml:
                with ZipFile(self.doc_path) as archive:
                    archive.getinfo("word/document.xml")
                return

            large_file_threshold = (
                self._get_config("document.large_file_threshold", 100) * 1024 * 1024
            )
            if self.file_size > large_file_threshold:  # 配置的阈值，默认100MB
                self.logger.warning(
                    "文档大小超过%.1fMB，python-docx 将在内存中解析该文件",
                    large_file_threshold / 1024 / 1024,
                )
            self.doc = Document(self.doc_path)
        except Exception as e:
            self.logger.error(f"加载文档失败: {str(e)}")
            raise DocumentError(f"无法加载文档 {self.doc_path}: {str(e)}")

    def _log_time(self, operation: str) -> None:
        """
        记录操作耗时

        Args:
            operation: 操作名称
        """
        current_time = time.time()
        elapsed = current_time - self.start_time
        self._processing_times[operation] = elapsed
        if operation != "init" and self.verbose:
            self.logger.debug(f"{operation} 耗时: {elapsed:.2f}秒")
        self.start_time = current_time

    def _extract_declared_count(self) -> Optional[int]:
        """
        从文档中提取批次声明的总记录数

        Returns:
            声明的总记录数，如果未找到则返回None
        """
        # 如果配置了跳过总记录数检查，直接返回None
        if self._skip_count_check:
            self.logger.info("根据配置跳过总记录数检查")
            return None

        return extract_declared_count(
            self.doc_path,
            max_paragraphs=self._max_paragraphs_to_search,
            max_tables=self._max_tables_to_search,
            document=self.doc,
        )

    def _process_paragraph(self, text: str) -> None:
        """Update document context from one non-empty body paragraph."""
        if not self.batch_number:
            self.batch_number = extract_batch_number(text)
            if self.batch_number:
                self.doc_structure.set_batch_number(self.batch_number)
                self.logger.info("提取到批次号: %s", self.batch_number)
                if self._build_structure:
                    self.doc_structure.add_node(
                        f"第{self.batch_number}批", "batch", level=0
                    )

        if "节能型汽车" in text:
            self.current_category = "节能型"
            self.current_type = None
            self.current_section = (
                self.doc_structure.add_node("节能型汽车", "section", content=text)
                if self._build_structure
                else None
            )
            self.current_subsection = None
            self.current_numbered_section = None
        elif "新能源汽车" in text:
            self.current_category = "新能源"
            self.current_type = None
            self.current_section = (
                self.doc_structure.add_node("新能源汽车", "section", content=text)
                if self._build_structure
                else None
            )
            self.current_subsection = None
            self.current_numbered_section = None
        elif text.startswith("（") and not any(char.isdigit() for char in text):
            self.current_type = text.strip()
            self.current_subsection = (
                self.doc_structure.add_node(
                    self.current_type,
                    "subsection",
                    content=text,
                    parent_node=self.current_section,
                )
                if self._build_structure
                else None
            )
            self.current_numbered_section = None
        elif self._build_structure and text.startswith(("1.", "2.", "3.", "4.", "5.")):
            self.current_numbered_section = self.doc_structure.add_node(
                text.strip(),
                "numbered_section",
                content=text,
                parent_node=self.current_subsection or self.current_section,
            )
        elif (
            self._build_structure
            and text.startswith("（")
            and any(number in text for number in "123456789")
        ):
            self.doc_structure.add_node(
                text.strip(),
                "numbered_subsection",
                content=text,
                parent_node=(
                    self.current_numbered_section
                    or self.current_subsection
                    or self.current_section
                ),
            )
        elif self._build_structure:
            if "勘误" in text or "说明" in text:
                node_type = "note"
            elif "更正" in text or "修改" in text:
                node_type = "correction"
            else:
                node_type = "text"
            self.doc_structure.add_node(
                text[:40] + "...",
                node_type,
                content=text,
                parent_node=self.current_section,
            )

    def _add_table_node(
        self,
        table_index: int,
        row_count: int,
        column_count: int,
        record_count: int,
    ) -> None:
        if not self._build_structure:
            return
        parent_node = (
            self.current_numbered_section
            or self.current_subsection
            or self.current_section
        )
        self.doc_structure.add_node(
            f"表格 {table_index + 1}",
            "table",
            metadata={
                "rows": row_count,
                "columns": column_count,
                "records": record_count,
                "category": self.current_category,
                "sub_type": self.current_type,
            },
            parent_node=parent_node,
        )

    def _process_standard_body(self) -> tuple[int, int, int]:
        """Process the body through python-docx for small documents."""
        if self.doc is None:
            raise ProcessingError("标准解析模式下文档尚未加载")

        table_count = 0
        row_count = 0
        error_count = 0
        tables = self.doc.tables
        table_lookup = {
            id(table._element): (index, table) for index, table in enumerate(tables)
        }

        for element in self.doc.element.body:
            try:
                if element.tag.endswith("p"):
                    text = element.text.strip()
                    if text:
                        self._process_paragraph(text)
                elif element.tag.endswith("tbl"):
                    table_count += 1
                    table_info = table_lookup.get(id(element))
                    if table_info is None:
                        raise ProcessingError("无法将 XML 表格映射到文档表格")
                    table_index, table = table_info
                    table_rows = len(table._tbl.tr_lst)
                    row_count += table_rows
                    table_cars = self.table_extractor.extract_car_info(
                        table,
                        table_index,
                        self.current_category,
                        self.current_type,
                        self.batch_number,
                    )
                    self.cars.extend(table_cars)
                    column_count = (
                        len(table.rows[0].cells)
                        if self._build_structure and table.rows
                        else 0
                    )
                    self._add_table_node(
                        table_index,
                        table_rows,
                        column_count,
                        len(table_cars),
                    )
                    if self.verbose:
                        self.logger.info(
                            "处理表格 %d, 提取到 %d 条记录",
                            table_index + 1,
                            len(table_cars),
                        )
            except Exception as exc:
                error_count += 1
                self.logger.error("处理元素出错: %s", exc)

        return table_count, row_count, error_count

    def _process_streaming_body(self) -> tuple[int, int, int]:
        """Process the main OOXML part without constructing a document DOM."""
        table_count = 0
        row_count = 0
        error_count = 0
        paragraph_count = 0
        table_declared_count: Optional[int] = None

        for element_type, value in iter_document_blocks(self.doc_path):
            try:
                if element_type == "paragraph":
                    paragraph_count += 1
                    text = str(value).strip()
                    if (
                        text
                        and not self._skip_count_check
                        and self.declared_count is None
                        and paragraph_count <= self._max_paragraphs_to_search
                    ):
                        self.declared_count = extract_declared_count_from_text(text)
                    if text:
                        self._process_paragraph(text)
                    continue

                table_index = table_count
                table_count += 1
                raw_row_count = 0
                column_count = 0
                first_rows: List[List[str]] = []
                last_rows: deque[List[str]] = deque(maxlen=3)

                def observed_rows() -> Any:
                    nonlocal raw_row_count, column_count
                    for raw_row in value:
                        raw_row_count += 1
                        if raw_row_count == 1 and self._build_structure:
                            column_count = len(raw_row)
                        if raw_row_count <= 3:
                            first_rows.append(raw_row)
                        last_rows.append(raw_row)
                        yield raw_row

                table_cars = self.table_extractor.extract_car_info_rows(
                    observed_rows(),
                    table_index,
                    self.current_category,
                    self.current_type,
                    self.batch_number,
                )
                row_count += raw_row_count

                if (
                    not self._skip_count_check
                    and table_declared_count is None
                    and table_count <= self._max_tables_to_search
                ):
                    rows_to_check = first_rows
                    if list(last_rows) != first_rows:
                        rows_to_check = first_rows + list(last_rows)
                    table_declared_count = extract_declared_count_from_rows(
                        rows_to_check
                    )
                self.cars.extend(table_cars)
                self._add_table_node(
                    table_index,
                    raw_row_count,
                    column_count,
                    len(table_cars),
                )
                if self.verbose:
                    self.logger.info(
                        "流式处理表格 %d, 提取到 %d 条记录",
                        table_index + 1,
                        len(table_cars),
                    )
            except Exception as exc:
                error_count += 1
                self.logger.error("流式处理元素出错: %s", exc)

        if self.declared_count is None:
            self.declared_count = table_declared_count

        return table_count, row_count, error_count

    def process(self) -> List[Dict[str, Any]]:
        """
        处理文档并返回所有车辆信息

        Returns:
            车辆信息字典列表

        Raises:
            ProcessingError: 处理文档失败
        """
        try:
            self.logger.info(f"开始处理文档: {self.doc_path}")
            self._log_time("init")

            if self._streaming_xml:
                table_count, row_count, error_count = self._process_streaming_body()
            else:
                table_count, row_count, error_count = self._process_standard_body()

            self._log_time("process")
            self.logger.info(
                f"文档处理完成: {table_count} 个表格, {row_count} 行, "
                f"{len(self.cars)} 条记录, {error_count} 个错误"
            )

            if error_count:
                raise ProcessingError(f"处理过程中出现 {error_count} 个元素错误")

            metrics = self.table_extractor.get_metrics()
            self.candidate_record_count = sum(
                item["candidate_count"] for item in metrics.values()
            )
            self.invalid_record_count = sum(
                item["invalid_count"] for item in metrics.values()
            )

            verification_start = time.time()
            if self._skip_verification:
                self.consistency_result = {
                    "status": "skipped",
                    "message": "已按配置跳过批次一致性验证",
                    "batch": self.batch_number,
                    "actual_count": len(self.cars),
                    "candidate_count": self.candidate_record_count,
                    "invalid_count": self.invalid_record_count,
                }
            else:
                if self.declared_count is None and not self._streaming_xml:
                    self.declared_count = self._extract_declared_count()
                self.consistency_result = verify_batch_consistency(
                    self.cars,
                    self.batch_number,
                    self.declared_count,
                    candidate_count=self.candidate_record_count,
                    invalid_count=self.invalid_record_count,
                )

            self.batch_results = verify_all_batches(self.cars)
            verification_time = time.time() - verification_start
            self.logger.info(
                "批次一致性验证结果: %s (耗时: %.2f秒)",
                self.consistency_result["status"],
                verification_time,
            )

            return self.cars

        except Exception as e:
            self.logger.error(f"处理文档失败: {str(e)}")
            if isinstance(e, ProcessingError):
                raise
            raise ProcessingError(f"处理文档 {self.doc_path} 失败: {str(e)}")
        finally:
            self.table_extractor.clear_cache()
            if not self._get_config("document.retain_document", False):
                self.doc = None
                gc.collect()

    def get_memory_usage(self) -> str:
        """
        获取当前进程的内存使用情况

        Returns:
            内存使用情况字符串
        """
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return f"{memory_info.rss / 1024 / 1024:.1f}MB"

    def save_to_csv(self, output_file: str) -> None:
        """
        将处理结果保存为CSV文件

        Args:
            output_file: 输出文件路径
        """
        if not self.cars:
            self.logger.warning("没有数据可保存")
            return

        write_csv_atomic(self.cars, output_file)
        self.logger.info("保存完成, 文件: %s, 记录数: %d", output_file, len(self.cars))


def process_doc(
    doc_path: str,
    output_file: Optional[str] = None,
    verbose: bool = False,
    config: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    处理单个文档的函数

    Args:
        doc_path: 文档路径
        output_file: 输出文件路径，如果提供则保存CSV文件
        verbose: 是否显示详细信息
        config: 配置信息

    Returns:
        车辆信息字典列表
    """
    processor = DocProcessor(doc_path, verbose, config)
    result = processor.process()
    if output_file and result:
        processor.save_to_csv(output_file)
    return result
