"""
测试文档节点模型
"""

import pytest
from typing import Dict, Any, List

from src.models.document_node import DocumentNode, DocumentStructure


class TestDocumentNode:
    """测试文档节点类"""

    def test_document_node_creation(self) -> None:
        """测试创建文档节点"""
        # 创建基本节点
        node = DocumentNode(title="测试标题", level=1, node_type="section")
        assert node.title == "测试标题"
        assert node.level == 1
        assert node.node_type == "section"
        assert node.content is None
        assert node.batch_number is None
        assert node.children == []
        assert node.metadata == {}

        # 创建带有所有属性的节点
        metadata = {"key": "value", "flag": True}
        node = DocumentNode(
            title="完整节点",
            level=2,
            node_type="table",
            content="表格内容",
            batch_number="1",
            metadata=metadata,
        )
        assert node.title == "完整节点"
        assert node.level == 2
        assert node.node_type == "table"
        assert node.content == "表格内容"
        assert node.batch_number == "1"
        assert node.metadata == metadata

        # 测试添加子节点
        child = DocumentNode(title="子节点", level=3, node_type="text")
        node.children.append(child)
        assert len(node.children) == 1
        assert node.children[0].title == "子节点"


class TestDocumentStructure:
    """测试文档结构类"""

    def test_document_structure_creation(self) -> None:
        """测试创建文档结构"""
        doc = DocumentStructure()
        assert doc.root.title == "文档结构"
        assert doc.root.level == 0
        assert doc.root.node_type == "root"
        assert doc.current_section is None
        assert doc.current_subsection is None
        assert doc.batch_number is None

    def test_add_node(self) -> None:
        """测试添加节点"""
        doc = DocumentStructure()

        # 添加一级节点
        section = doc.add_node(title="一级标题", node_type="section")
        assert section.title == "一级标题"
        assert section.level == 1
        assert section.node_type == "section"
        assert len(doc.root.children) == 1
        assert doc.root.children[0] == section

        # 添加二级节点
        subsection = doc.add_node(title="二级标题", node_type="subsection")
        assert subsection.title == "二级标题"
        assert subsection.level == 2
        assert subsection.node_type == "subsection"

        # 添加带内容的节点
        text_node = doc.add_node(
            title="文本节点", node_type="text", content="这是一段文本内容"
        )
        assert text_node.content == "这是一段文本内容"

        # 添加带元数据的节点
        metadata = {"author": "测试人员", "date": "2023-01-01"}
        meta_node = doc.add_node(
            title="元数据节点", node_type="note", metadata=metadata
        )
        assert meta_node.metadata == metadata

        # 测试指定父节点
        parent = doc.add_node(title="父节点", node_type="section")
        child = doc.add_node(title="子节点", node_type="text", parent_node=parent)
        assert child in parent.children
        assert len(parent.children) == 1

    def test_add_node_with_default_levels(self) -> None:
        """测试添加节点时的默认级别设置"""
        doc = DocumentStructure()

        # 测试各种类型的默认级别
        section = doc.add_node(title="一级", node_type="section")
        assert section.level == 1

        subsection = doc.add_node(title="二级", node_type="subsection")
        assert subsection.level == 2

        numbered_section = doc.add_node(title="三级", node_type="numbered_section")
        assert numbered_section.level == 3

        numbered_subsection = doc.add_node(
            title="四级", node_type="numbered_subsection"
        )
        assert numbered_subsection.level == 4

        other = doc.add_node(title="其他", node_type="other")
        assert other.level == 5

        # 测试显式指定级别
        custom = doc.add_node(title="自定义", node_type="section", level=10)
        assert custom.level == 10

    def test_add_node_hierarchy(self) -> None:
        """测试节点层级关系"""
        doc = DocumentStructure()

        # 创建一级节点
        section1 = doc.add_node(title="一级标题1", node_type="section")
        doc.current_section = section1

        # 在一级节点下添加二级节点
        subsection1 = doc.add_node(title="二级标题1", node_type="subsection")
        doc.current_subsection = subsection1

        # 在二级节点下添加内容节点
        text1 = doc.add_node(title="文本1", node_type="text")

        # 验证层级关系
        assert section1 in doc.root.children
        assert subsection1 in section1.children
        assert text1 in subsection1.children

        # 创建另一个一级节点
        section2 = doc.add_node(title="一级标题2", node_type="section")
        doc.current_section = section2
        doc.current_subsection = None

        # 在新一级节点下添加内容节点
        text2 = doc.add_node(title="文本2", node_type="text")

        # 验证层级关系
        assert section2 in doc.root.children
        assert text2 in section2.children

        # 没有当前节点的情况
        doc.current_section = None
        text3 = doc.add_node(title="文本3", node_type="text")
        assert text3 in doc.root.children

    def test_set_batch_number(self) -> None:
        """测试设置批次号"""
        doc = DocumentStructure()
        assert doc.batch_number is None

        # 设置批次号
        doc.set_batch_number("123")
        assert doc.batch_number == "123"

        # 添加节点时应继承批次号
        node = doc.add_node(title="测试节点", node_type="section")
        assert node.batch_number == "123"

        # 更新批次号
        doc.set_batch_number("456")
        assert doc.batch_number == "456"

        # 新节点应使用新批次号
        node2 = doc.add_node(title="测试节点2", node_type="section")
        assert node2.batch_number == "456"

    def test_to_dict(self) -> None:
        """测试转换为字典格式"""
        doc = DocumentStructure()

        # 设置批次号
        doc.set_batch_number("1")

        # 添加一些节点
        section = doc.add_node(
            title="一级标题", node_type="section", content="一级内容"
        )
        doc.current_section = section

        subsection = doc.add_node(
            title="二级标题",
            node_type="subsection",
            content="二级内容",
            metadata={"key": "value"},
        )
        doc.current_subsection = subsection

        doc.add_node(title="文本", node_type="text", content="文本内容")

        # 转换为字典
        result = doc.to_dict()

        # 验证结果
        assert result["title"] == "文档结构"
        assert result["type"] == "root"
        assert result["level"] == 0
        assert len(result["children"]) == 1

        # 验证一级节点
        section_dict = result["children"][0]
        assert section_dict["title"] == "一级标题"
        assert section_dict["type"] == "section"
        assert section_dict["content"] == "一级内容"
        assert section_dict["batch_number"] == "1"
        assert len(section_dict["children"]) == 1

        # 验证二级节点
        subsection_dict = section_dict["children"][0]
        assert subsection_dict["title"] == "二级标题"
        assert subsection_dict["type"] == "subsection"
        assert subsection_dict["content"] == "二级内容"
        assert subsection_dict["batch_number"] == "1"
        assert subsection_dict["metadata"] == {"key": "value"}
        assert len(subsection_dict["children"]) == 1

        # 验证文本节点
        text_dict = subsection_dict["children"][0]
        assert text_dict["title"] == "文本"
        assert text_dict["type"] == "text"
        assert text_dict["content"] == "文本内容"
