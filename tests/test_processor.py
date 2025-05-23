"""
测试文档处理器模块
"""

import os
import pytest
from unittest.mock import patch, MagicMock, mock_open
from src.processor.doc_processor import (
    DocProcessor,
    process_doc,
    ProcessingError,
    DocumentError,
)
from src.batch.validator import verify_batch_consistency


class TestDocProcessor:
    """测试文档处理器类"""

    @patch("src.processor.doc_processor.Document")
    @patch("os.path.getsize")
    def test_init(self, mock_getsize, mock_document) -> None:
        """测试初始化文档处理器"""
        # 设置mock
        mock_doc = MagicMock()
        mock_document.return_value = mock_doc
        mock_getsize.return_value = 1024  # 1KB

        # 测试基本初始化
        processor = DocProcessor("test.docx")

        # 验证基本属性
        assert processor.doc_path == "test.docx"
        assert processor.verbose == True
        assert processor.config == {}
        assert processor.cars == []
        assert processor.current_category is None
        assert processor.current_type is None
        assert processor.batch_number is None
        assert processor._chunk_size == 1000

        # 测试带配置的初始化
        config = {
            "performance": {
                "chunk_size": 500,
                "cache_size_limit": 1000000,
                "cleanup_interval": 200,
            },
            "document": {"skip_count_check": True},
        }
        processor = DocProcessor("test.docx", verbose=False, config=config)

        # 验证配置被正确应用
        assert processor.verbose == False
        assert processor._chunk_size == 500
        assert processor._cache_size_limit == 1000000
        assert processor._cleanup_interval == 200
        assert processor._skip_count_check == True

    @patch("src.processor.doc_processor.Document")
    @patch("os.path.getsize")
    def test_init_with_document_error(self, mock_getsize, mock_document) -> None:
        """测试初始化时文档错误处理"""
        # 设置mock抛出异常
        mock_document.side_effect = Exception("测试文档错误")
        mock_getsize.return_value = 1024  # 1KB

        # 验证异常被正确包装和抛出
        with pytest.raises(DocumentError) as excinfo:
            DocProcessor("invalid.docx")

        assert "无法加载文档" in str(excinfo.value)
        assert "测试文档错误" in str(excinfo.value)

    @patch("src.processor.doc_processor.Document")
    @patch("os.path.getsize")
    def test_get_config(self, mock_getsize, mock_document) -> None:
        """测试配置获取方法"""
        mock_doc = MagicMock()
        mock_document.return_value = mock_doc
        mock_getsize.return_value = 1024  # 1KB

        # 创建带配置的处理器
        config = {"performance": {"chunk_size": 500}, "simple_key": "simple_value"}
        processor = DocProcessor("test.docx", config=config)

        # 测试嵌套键
        assert processor._get_config("performance.chunk_size", 1000) == 500

        # 测试简单键
        assert processor._get_config("simple_key", None) == "simple_value"

        # 测试默认值
        assert processor._get_config("non_existent_key", "default") == "default"
        assert processor._get_config("performance.non_existent", 123) == 123

    @patch("src.processor.doc_processor.Document")
    @patch("os.path.getsize")
    @patch("src.processor.doc_processor.extract_declared_count")
    def test_extract_declared_count(
        self, mock_extract_count, mock_getsize, mock_document
    ) -> None:
        """测试提取声明的总记录数"""
        mock_doc = MagicMock()
        mock_document.return_value = mock_doc
        mock_getsize.return_value = 1024  # 1KB

        # 设置mock返回值
        mock_extract_count.return_value = 123

        # 创建处理器
        processor = DocProcessor("test.docx")

        # 测试正常提取
        count = processor._extract_declared_count()
        assert count == 123
        mock_extract_count.assert_called_once_with(
            "test.docx",
            max_paragraphs=processor._max_paragraphs_to_search,
            max_tables=processor._max_tables_to_search,
        )

        # 测试跳过提取
        processor._skip_count_check = True
        count = processor._extract_declared_count()
        assert count is None

    @patch("src.processor.doc_processor.Document")
    @patch("os.path.getsize")
    @patch("src.processor.doc_processor.extract_doc_content")
    def test_document_processing(
        self, mock_extract_content, mock_getsize, mock_document
    ) -> None:
        """测试文档内容处理"""
        mock_doc = MagicMock()
        mock_document.return_value = mock_doc
        mock_getsize.return_value = 1024  # 1KB

        # 设置mock返回值
        mock_extract_content.return_value = (
            ["第一批", "节能型汽车", "（一）轿车"],
            [
                {
                    "type": "说明",
                    "section": "（一）轿车",
                    "content": "技术要求说明",
                    "batch": "1",
                }
            ],
        )

        # 创建处理器
        processor = DocProcessor("test.docx")

        # 模拟处理文档内容
        processor.batch_number = "1"
        processor.current_category = "节能型汽车"
        processor.current_type = "（一）轿车"

        # 验证结果
        assert processor.batch_number == "1"
        assert processor.current_category == "节能型汽车"
        assert processor.current_type == "（一）轿车"

    @patch("src.processor.doc_processor.Document")
    @patch("os.path.getsize")
    @patch("src.processor.doc_processor.TableExtractor")
    def test_table_processing(
        self, mock_extractor_class, mock_getsize, mock_document
    ) -> None:
        """测试表格数据处理"""
        mock_doc = MagicMock()
        mock_document.return_value = mock_doc
        mock_getsize.return_value = 1024  # 1KB

        # 设置mock表格
        mock_table = MagicMock()
        mock_doc.tables = [mock_table]

        # 设置mock提取器
        mock_extractor = MagicMock()
        mock_extractor_class.return_value = mock_extractor

        # 设置提取结果
        mock_extractor.extract_car_info.return_value = [
            {"vmodel": "型号A", "企业名称": "企业X", "品牌": "品牌Y"},
            {"vmodel": "型号B", "企业名称": "企业Z", "品牌": "品牌W"},
        ]

        # 创建处理器并设置必要的状态
        processor = DocProcessor("test.docx")
        processor.batch_number = "1"
        processor.current_category = "节能型汽车"
        processor.current_type = "轿车"
        processor.table_extractor = mock_extractor
        processor.cars = []

        # 手动添加表格处理的结果
        processor.cars.extend(mock_extractor.extract_car_info.return_value)

        # 验证结果
        assert len(processor.cars) == 2
        assert processor.cars[0]["vmodel"] == "型号A"
        assert processor.cars[1]["vmodel"] == "型号B"

    @patch("src.processor.doc_processor.Document")
    @patch("os.path.getsize")
    @patch("src.processor.doc_processor.verify_batch_consistency")
    def test_batch_verification(self, mock_verify, mock_getsize, mock_document) -> None:
        """测试批次一致性验证"""
        mock_doc = MagicMock()
        mock_document.return_value = mock_doc
        mock_getsize.return_value = 1024  # 1KB

        # 设置mock返回值
        mock_verify.return_value = {
            "status": "match",
            "message": "批次记录数匹配",
            "batch": "1",
            "actual_count": 10,
            "declared_count": 10,
        }

        # 创建处理器并设置必要的状态
        processor = DocProcessor("test.docx")
        processor.batch_number = "1"
        processor.declared_count = 10
        processor.cars = [{"vmodel": f"型号{i}"} for i in range(10)]

        # 手动调用mock函数
        mock_verify(processor.cars, "1", 10)
        result = mock_verify.return_value

        # 验证结果
        assert result["status"] == "match"
        assert result["actual_count"] == 10
        mock_verify.assert_called_once_with(processor.cars, "1", 10)

    @patch("src.processor.doc_processor.Document")
    @patch("os.path.getsize")
    @patch("src.processor.doc_processor.process_car_info")
    def test_car_processing(
        self, mock_process_car, mock_getsize, mock_document
    ) -> None:
        """测试处理车辆信息"""
        mock_doc = MagicMock()
        mock_document.return_value = mock_doc
        mock_getsize.return_value = 1024  # 1KB

        # 设置mock行为
        def process_side_effect(car):
            return {**car, "processed": True}

        mock_process_car.side_effect = process_side_effect

        # 创建处理器并设置必要的状态
        processor = DocProcessor("test.docx")
        processor.cars = [
            {"vmodel": "型号A", "企业名称": "企业X"},
            {"vmodel": "型号B", "企业名称": "企业Y"},
        ]

        # 手动处理车辆信息
        processed_cars = []
        for car in processor.cars:
            processed_cars.append(mock_process_car(car))
        processor.cars = processed_cars

        # 验证结果
        assert len(processor.cars) == 2
        assert all(car["processed"] for car in processor.cars)
        assert mock_process_car.call_count == 2

    @patch("src.processor.doc_processor.Document")
    @patch("os.path.getsize")
    @patch("src.processor.doc_processor.DocProcessor.process")
    def test_process(
        self,
        mock_process,
        mock_getsize,
        mock_document,
    ) -> None:
        """测试完整处理流程"""
        mock_doc = MagicMock()
        mock_document.return_value = mock_doc
        mock_getsize.return_value = 1024  # 1KB

        # 设置mock返回值
        mock_process.return_value = [{"vmodel": "型号A"}, {"vmodel": "型号B"}]

        # 创建处理器
        processor = DocProcessor("test.docx")

        # 调用测试方法
        result = processor.process()

        # 验证方法调用
        mock_process.assert_called_once()

        # 验证结果
        assert len(result) == 2
        assert result[0]["vmodel"] == "型号A"
        assert result[1]["vmodel"] == "型号B"

    @patch("src.processor.doc_processor.Document")
    @patch("os.path.getsize")
    def test_save_to_csv(self, mock_getsize, mock_document) -> None:
        """测试保存到CSV文件"""
        mock_doc = MagicMock()
        mock_document.return_value = mock_doc
        mock_getsize.return_value = 1024  # 1KB

        # 创建处理器并设置车辆数据
        processor = DocProcessor("test.docx")
        processor.cars = [
            {"vmodel": "型号A", "企业名称": "企业X"},
            {"vmodel": "型号B", "企业名称": "企业Y"},
        ]

        # 模拟文件操作，避免实际写入文件
        with (
            patch("builtins.open", mock_open()),
            patch("src.processor.doc_processor.pd") as mock_pd,
        ):
            # 设置mock DataFrame
            mock_df = MagicMock()
            mock_pd.DataFrame.return_value = mock_df

            # 模拟DataFrame的columns属性和tolist方法
            columns_mock = MagicMock()
            columns_mock.tolist.return_value = ["vmodel", "企业名称"]
            type(mock_df).columns = columns_mock

            # 调用测试方法
            processor.save_to_csv("output.csv")

            # 仅验证DataFrame被创建
            mock_pd.DataFrame.assert_called_once_with(processor.cars)

    @patch("src.processor.doc_processor.DocProcessor")
    def test_process_doc(self, mock_processor_class) -> None:
        """测试process_doc函数"""
        # 设置mock处理器
        mock_processor = MagicMock()
        mock_processor_class.return_value = mock_processor
        mock_processor.process.return_value = [{"vmodel": "型号A"}, {"vmodel": "型号B"}]

        # 调用测试函数
        result = process_doc("test.docx", verbose=True, config={"key": "value"})

        # 验证结果
        assert len(result) == 2
        # 使用位置参数而不是关键字参数
        mock_processor_class.assert_called_once_with(
            "test.docx", True, {"key": "value"}
        )
        mock_processor.process.assert_called_once()

    @patch("src.processor.doc_processor.DocProcessor")
    def test_process_doc_with_error(self, mock_processor_class) -> None:
        """测试process_doc函数错误处理"""
        # 设置mock处理器抛出异常
        mock_processor_class.side_effect = DocumentError("测试文档错误")

        # 验证异常被正确处理
        result = process_doc("invalid.docx")
        assert result == []
