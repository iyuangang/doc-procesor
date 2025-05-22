"""
文档节点模型 - 定义文档结构的数据类
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


@dataclass
class DocumentNode:
    """
    文档节点类，用于构建文档树结构

    Attributes:
        title: 节点标题
        level: 节点级别（0为根节点，1为一级标题，以此类推）
        node_type: 节点类型，可以是 'section', 'subsection', 'table', 'text', 'note', 'correction'
        content: 节点内容
        batch_number: 批次号
        children: 子节点列表
        metadata: 额外元数据
    """

    title: str
    level: int
    node_type: str  # 'section', 'subsection', 'table', 'text', 'note', 'correction'
    content: Optional[str] = None
    batch_number: Optional[str] = None
    children: List["DocumentNode"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class DocumentStructure:
    """
    文档结构类，用于构建和管理文档的层级结构

    Attributes:
        root: 根节点
        current_section: 当前一级节点
        current_subsection: 当前二级节点
        batch_number: 当前批次号
    """

    def __init__(self) -> None:
        """初始化文档结构"""
        self.root = DocumentNode("文档结构", 0, "root")
        self.current_section: Optional[DocumentNode] = None
        self.current_subsection: Optional[DocumentNode] = None
        self.batch_number: Optional[str] = None

    def add_node(
        self,
        title: str,
        node_type: str,
        content: Optional[str] = None,
        level: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_node: Optional[DocumentNode] = None,
    ) -> DocumentNode:
        """
        添加新节点到文档树

        Args:
            title: 节点标题
            node_type: 节点类型
            content: 节点内容
            level: 节点级别
            metadata: 节点元数据
            parent_node: 父节点

        Returns:
            新创建的节点
        """
        if level is None:
            if node_type == "section":
                level = 1
            elif node_type == "subsection":
                level = 2
            elif node_type == "numbered_section":
                level = 3
            elif node_type == "numbered_subsection":
                level = 4
            else:
                level = 5

        node = DocumentNode(
            title=title,
            level=level,
            node_type=node_type,
            content=content,
            batch_number=self.batch_number,
            metadata=metadata or {},
        )

        # 如果指定了父节点，直接添加到父节点
        if parent_node:
            parent_node.children.append(node)
            return node

        # 否则使用默认的层级逻辑
        if level == 1:
            self.root.children.append(node)
        elif level == 2:
            if self.current_section:
                self.current_section.children.append(node)
            else:
                self.root.children.append(node)
        else:
            if self.current_subsection:
                self.current_subsection.children.append(node)
            elif self.current_section:
                self.current_section.children.append(node)
            else:
                self.root.children.append(node)

        return node

    def set_batch_number(self, batch_number: str) -> None:
        """
        设置批次号

        Args:
            batch_number: 批次号
        """
        self.batch_number = batch_number

    def to_dict(self) -> Dict[str, Any]:
        """
        将文档结构转换为字典格式

        Returns:
            字典格式的文档结构
        """

        def node_to_dict(node: DocumentNode) -> Dict[str, Any]:
            return {
                "title": node.title,
                "type": node.node_type,
                "level": node.level,
                "content": node.content,
                "batch_number": node.batch_number,
                "metadata": node.metadata,
                "children": [node_to_dict(child) for child in node.children],
            }

        return node_to_dict(self.root)
