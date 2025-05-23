"""
测试文档解析模块
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from src.document.parser import (
    extract_doc_content,
    get_table_type,
    extract_declared_count,
)


class TestDocumentParser:
    """测试文档解析模块"""

    @patch("src.document.parser.Document")
    def test_extract_doc_content_basic(self, mock_document):
        """测试基本的文档内容提取"""
        # 创建模拟的Document对象
        mock_doc = MagicMock()
        mock_document.return_value = mock_doc

        # 模拟段落
        mock_paragraphs = [
            MagicMock(text="第一批"),
            MagicMock(text="节能型汽车"),
            MagicMock(text="（一）轿车"),
            MagicMock(text="企业A 型号X"),
            MagicMock(text=""),
            MagicMock(text="勘误：型号X应为型号Y"),
        ]
        mock_doc.paragraphs = mock_paragraphs

        # 调用测试函数
        paragraphs, extra_info = extract_doc_content("dummy_path.docx")

        # 验证结果
        assert len(paragraphs) == 4
        assert paragraphs[0] == "第一批"
        assert paragraphs[1] == "节能型汽车"
        assert paragraphs[2] == "（一）轿车"
        assert paragraphs[3] == "企业A 型号X"

        assert len(extra_info) == 1
        assert extra_info[0]["type"] == "勘误"
        assert extra_info[0]["section"] == "（一）轿车"
        assert "型号X应为型号Y" in extra_info[0]["content"]
        assert extra_info[0]["batch"] == "1"

    @patch("src.document.parser.Document")
    def test_extract_doc_content_with_batch(self, mock_document):
        """测试提取带批次号的文档内容"""
        # 创建模拟的Document对象
        mock_doc = MagicMock()
        mock_document.return_value = mock_doc

        # 模拟段落
        mock_paragraphs = [
            MagicMock(text="第二十三批新能源汽车推广应用推荐车型目录"),
            MagicMock(text="新能源汽车"),
            MagicMock(text="（一）纯电动乘用车"),
        ]
        mock_doc.paragraphs = mock_paragraphs

        # 调用测试函数
        paragraphs, extra_info = extract_doc_content("dummy_path.docx")

        # 验证结果
        assert len(paragraphs) == 3
        assert paragraphs[0] == "第二十三批新能源汽车推广应用推荐车型目录"
        assert paragraphs[1] == "新能源汽车"
        assert paragraphs[2] == "（一）纯电动乘用车"

    @patch("src.document.parser.Document")
    def test_extract_doc_content_with_extra_info(self, mock_document):
        """测试提取带额外信息的文档内容"""
        # 创建模拟的Document对象
        mock_doc = MagicMock()
        mock_document.return_value = mock_doc

        # 模拟段落
        mock_paragraphs = [
            MagicMock(text="第一批"),
            MagicMock(text="关于第一批车型的说明"),
            MagicMock(text="这是一些额外的说明文本"),
            MagicMock(text=""),  # 空行
            MagicMock(text="节能型汽车"),
            MagicMock(text="（一）轿车"),
            MagicMock(text="技术要求：符合相关标准"),
            MagicMock(text="具体要求如下"),
        ]
        mock_doc.paragraphs = mock_paragraphs

        # 调用测试函数
        paragraphs, extra_info = extract_doc_content("dummy_path.docx")

        # 验证结果
        assert len(paragraphs) == 3
        assert paragraphs[0] == "第一批"
        assert paragraphs[1] == "节能型汽车"
        assert paragraphs[2] == "（一）轿车"

        assert len(extra_info) == 2
        assert extra_info[0]["type"] == "政策"
        assert "第一批车型的说明" in extra_info[0]["content"]
        assert "额外的说明文本" in extra_info[0]["content"]

        assert extra_info[1]["type"] == "说明"
        assert "技术要求" in extra_info[1]["content"]
        assert "具体要求" in extra_info[1]["content"]

    def test_get_table_type(self):
        """测试表格类型判断"""
        # 测试节能型汽车
        headers = ["序号", "企业名称", "品牌", "型号"]
        category, sub_type = get_table_type(headers, "节能型汽车", "轿车")
        assert category == "节能型"
        assert sub_type == "轿车"

        # 测试新能源汽车
        headers = ["序号", "企业名称", "品牌", "型号"]
        category, sub_type = get_table_type(headers, "新能源汽车", "纯电动乘用车")
        assert category == "新能源"
        assert sub_type == "纯电动乘用车"

        # 测试特殊表头组合
        headers = ["序号", "企业名称", "型式", "档位数"]
        category, sub_type = get_table_type(headers, "节能型汽车", "轿车")
        assert category == "节能型"
        assert sub_type == "轿车"

    def test_get_table_type_missing_columns(self):
        """测试表格类型判断 - 缺少必要列"""
        headers = ["序号", "品牌", "型号"]  # 缺少企业名称
        with pytest.raises(ValueError) as excinfo:
            get_table_type(headers, "节能型汽车", "轿车")
        assert "缺少必要的列" in str(excinfo.value)

    @patch("src.document.parser.Document")
    def test_extract_declared_count(self, mock_document):
        """测试提取声明的总记录数"""
        # 创建模拟的Document对象
        mock_doc = MagicMock()
        mock_document.return_value = mock_doc

        # 模拟段落
        mock_paragraphs = [
            MagicMock(text="第一批推荐目录"),
            MagicMock(text="本批次共计123款车型"),
            MagicMock(text="其他内容"),
        ]
        mock_doc.paragraphs = mock_paragraphs

        # 模拟表格
        mock_doc.tables = []

        # 调用测试函数
        count = extract_declared_count("dummy_path.docx")

        # 验证结果
        assert count == 123

    @patch("src.document.parser.Document")
    def test_extract_declared_count_in_table(self, mock_document):
        """测试从表格中提取声明的总记录数"""
        # 创建模拟的Document对象
        mock_doc = MagicMock()
        mock_document.return_value = mock_doc

        # 模拟段落（不包含总记录数）
        mock_paragraphs = [
            MagicMock(text="第一批推荐目录"),
            MagicMock(text="其他内容"),
        ]
        mock_doc.paragraphs = mock_paragraphs

        # 模拟表格
        mock_table = MagicMock()

        # 创建模拟行
        mock_row = MagicMock()

        # 创建模拟单元格
        mock_cell1 = MagicMock()
        mock_cell1.text = "合计"

        mock_cell2 = MagicMock()
        mock_cell2.text = "456"  # 数字单元格

        # 设置行的单元格
        mock_row.cells = [mock_cell1, mock_cell2]

        # 设置表格的行
        mock_table.rows = [mock_row]

        mock_doc.tables = [mock_table]

        # 调用测试函数
        count = extract_declared_count("dummy_path.docx")

        # 验证结果
        assert count == 456
