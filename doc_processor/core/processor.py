"""
文档处理器核心模块
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from docx import Document

from doc_processor.config import ProcessorConfig
from doc_processor.exceptions import DocumentError, ProcessingError
from doc_processor.extractors import BatchExtractor, ContentExtractor, TableExtractor
from doc_processor.models import CarInfo, CarInfoCollection, DocumentStructure
from doc_processor.parsers import DocxParser
from doc_processor.utils import (
    TimingContext,
    create_logger,
    print_info,
    print_success,
    print_warning,
)

# 创建日志记录器
logger = create_logger(__name__)


class DocProcessor:
    """
    文档处理器类，负责协调各组件处理文档

    Attributes:
        config: 处理器配置
        verbose: 是否显示详细信息
    """

    def __init__(self, config: Optional[ProcessorConfig] = None) -> None:
        """
        初始化文档处理器

        Args:
            config: 处理器配置对象
        """
        self.config = config or ProcessorConfig()
        self.verbose = self.config.verbose

    def process_file(self, file_path: Union[str, Path]) -> CarInfoCollection:
        """
        处理单个文档文件

        Args:
            file_path: 文档文件路径

        Returns:
            车辆信息集合

        Raises:
            ProcessingError: 处理文件出错
            DocumentError: 文档错误
        """
        file_path_str = str(file_path)
        if not os.path.exists(file_path_str):
            raise DocumentError(f"文件不存在: {file_path_str}")

        if not file_path_str.lower().endswith(".docx"):
            raise DocumentError(f"不支持的文件格式: {file_path_str}")

        try:
            if self.verbose:
                print_info(f"正在处理文件: {os.path.basename(file_path_str)}")
                logger.info(f"开始处理文件: {file_path_str}")

            # 使用计时上下文
            with TimingContext("处理文档", verbose=self.verbose) as timing_ctx:
                # 解析文档结构
                parser = DocxParser(file_path_str)
                doc_structure = parser.parse()
                timing_ctx.log_step("解析文档结构")

                # 提取批次号和总记录数
                docx_doc = Document(file_path_str)
                batch_extractor = BatchExtractor(
                    docx_doc,
                    max_paragraphs=self.config.max_paragraphs_to_search,
                    verbose=self.verbose,
                )
                batch_number, declared_count = batch_extractor.extract()
                timing_ctx.log_step("提取批次号")

                # 提取文档内容
                content_extractor = ContentExtractor(docx_doc, verbose=self.verbose)
                paragraphs, extra_info = content_extractor.extract()
                timing_ctx.log_step("提取文档内容")

                # 创建车辆信息集合
                car_collection = CarInfoCollection()

                # 处理文档中的表格
                current_category = None
                current_type = None
                tables = parser.get_tables()

                # 限制处理的表格数量
                max_tables = min(len(tables), self.config.max_tables_to_search)
                tables_processed = 0

                for idx, table in enumerate(tables[:max_tables]):
                    # 更新当前分类和类型
                    for node in doc_structure.find_nodes_by_type("section"):
                        if node.title and "节能" in node.title:
                            current_category = "节能型"
                        elif node.title and any(
                            term in node.title
                            for term in ["新能源", "电动", "混合动力"]
                        ):
                            current_category = "新能源"

                    for node in doc_structure.find_nodes_by_type("subsection"):
                        if node.title and "乘用车" in node.title:
                            current_type = "（一）乘用车"
                        elif node.title and "客车" in node.title:
                            current_type = "（二）客车"
                        elif node.title and "专用车" in node.title:
                            current_type = "（三）专用车"

                    # 提取表格中的车辆信息
                    extractor = TableExtractor(
                        table,
                        idx,
                        batch_number,
                        current_category,
                        current_type,
                        chunk_size=self.config.chunk_size,
                        verbose=self.verbose,
                    )
                    table_cars = extractor.extract()

                    # 添加到集合中
                    for car in table_cars.cars:
                        car_collection.add(car)

                    tables_processed += 1
                    if self.verbose:
                        print_info(
                            f"表格 {idx+1} 提取了 {len(table_cars.cars)} 条车辆信息"
                        )

                timing_ctx.log_step("提取表格数据")

                # 验证总记录数
                if not self.config.skip_count_check and declared_count is not None:
                    actual_count = len(car_collection)
                    if actual_count != declared_count:
                        print_warning(
                            f"记录数不匹配: 声明 {declared_count} 条，实际提取 {actual_count} 条"
                        )
                        logger.warning(
                            f"记录数不匹配: 声明 {declared_count} 条，实际提取 {actual_count} 条"
                        )
                    else:
                        print_success(f"成功提取 {actual_count} 条记录，与声明数量一致")
                else:
                    print_success(f"成功提取 {len(car_collection)} 条记录")

            # 返回车辆信息集合
            return car_collection

        except Exception as e:
            logger.error(f"处理文件失败: {file_path_str}", exc_info=True)
            raise ProcessingError(f"处理文件失败: {str(e)}", file_path_str)

    def process_directory(
        self, dir_path: Union[str, Path], recursive: bool = False
    ) -> Dict[str, CarInfoCollection]:
        """
        处理目录中的所有文档

        Args:
            dir_path: 目录路径
            recursive: 是否递归处理子目录

        Returns:
            文件路径到车辆信息集合的映射

        Raises:
            ProcessingError: 处理目录出错
        """
        dir_path_str = str(dir_path)
        if not os.path.exists(dir_path_str):
            raise ProcessingError(f"目录不存在: {dir_path_str}")

        if not os.path.isdir(dir_path_str):
            raise ProcessingError(f"路径不是目录: {dir_path_str}")

        try:
            results: Dict[str, CarInfoCollection] = {}

            # 获取文件列表
            files = []
            if recursive:
                for root, _, filenames in os.walk(dir_path_str):
                    for filename in filenames:
                        if filename.lower().endswith(".docx"):
                            files.append(os.path.join(root, filename))
            else:
                files = [
                    os.path.join(dir_path_str, f)
                    for f in os.listdir(dir_path_str)
                    if f.lower().endswith(".docx")
                ]

            if not files:
                print_warning(f"目录中没有找到.docx文件: {dir_path_str}")
                return results

            # 处理每个文件
            for file_path in files:
                try:
                    results[file_path] = self.process_file(file_path)
                except (ProcessingError, DocumentError) as e:
                    print_warning(
                        f"处理文件失败: {os.path.basename(file_path)} - {str(e)}"
                    )
                    logger.warning(f"处理文件失败: {file_path} - {str(e)}")

            # 返回结果
            return results

        except Exception as e:
            logger.error(f"处理目录失败: {dir_path_str}", exc_info=True)
            raise ProcessingError(f"处理目录失败: {str(e)}", dir_path_str)

    def preview_document(self, file_path: Union[str, Path]) -> DocumentStructure:
        """
        预览文档结构，不提取详细内容

        Args:
            file_path: 文档文件路径

        Returns:
            文档结构

        Raises:
            DocumentError: 文档错误
        """
        file_path_str = str(file_path)
        if not os.path.exists(file_path_str):
            raise DocumentError(f"文件不存在: {file_path_str}")

        if not file_path_str.lower().endswith(".docx"):
            raise DocumentError(f"不支持的文件格式: {file_path_str}")

        try:
            # 解析文档结构
            parser = DocxParser(file_path_str)
            doc_structure = parser.parse()

            # 只提取批次号
            docx_doc = Document(file_path_str)
            batch_extractor = BatchExtractor(
                docx_doc,
                max_paragraphs=self.config.max_paragraphs_to_search,
                verbose=self.verbose,
            )
            batch_number, declared_count = batch_extractor.extract()

            if batch_number:
                print_info(f"批次号: {batch_number}")
            if declared_count:
                print_info(f"总记录数: {declared_count}")

            # 返回文档结构
            return doc_structure

        except Exception as e:
            logger.error(f"预览文档失败: {file_path_str}", exc_info=True)
            raise DocumentError(f"预览文档失败: {str(e)}", file_path_str)
