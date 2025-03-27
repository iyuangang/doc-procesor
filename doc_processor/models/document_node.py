"""
文档节点模型模块，定义文档结构
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DocumentNode:
    """
    文档节点类，用于构建文档树结构

    Attributes:
        title: 节点标题
        level: 节点层级，数值越小表示越靠近根节点
        node_type: 节点类型，如'section', 'subsection', 'table', 'text'等
        content: 节点内容，可选
        batch_number: 批次号，可选
        children: 子节点列表
        metadata: 元数据字典
    """

    title: str
    level: int
    node_type: str  # 'section', 'subsection', 'table', 'text', 'note', 'correction'
    content: Optional[str] = None
    batch_number: Optional[str] = None
    children: List["DocumentNode"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_child(self, node: "DocumentNode") -> "DocumentNode":
        """
        添加子节点

        Args:
            node: 要添加的子节点

        Returns:
            添加的子节点
        """
        self.children.append(node)
        return node

    def find_by_title(self, title: str) -> Optional["DocumentNode"]:
        """
        根据标题查找节点

        Args:
            title: 要查找的标题

        Returns:
            匹配的节点，如果未找到则返回None
        """
        if self.title == title:
            return self

        for child in self.children:
            result = child.find_by_title(title)
            if result:
                return result

        return None

    def find_by_type(self, node_type: str) -> List["DocumentNode"]:
        """
        根据节点类型查找节点

        Args:
            node_type: 要查找的节点类型

        Returns:
            匹配的节点列表
        """
        result = []
        if self.node_type == node_type:
            result.append(self)

        for child in self.children:
            result.extend(child.find_by_type(node_type))

        return result

    def to_dict(self) -> Dict[str, Any]:
        """
        将节点转换为字典

        Returns:
            节点的字典表示
        """
        return {
            "title": self.title,
            "level": self.level,
            "type": self.node_type,
            "content": self.content,
            "batch_number": self.batch_number,
            "metadata": self.metadata,
            "children": [child.to_dict() for child in self.children],
        }

    def __str__(self) -> str:
        """
        字符串表示

        Returns:
            节点的字符串表示
        """
        return f"{self.node_type}({self.level}): {self.title}"


class DocumentStructure:
    """
    文档结构类，用于构建和管理文档的层级结构

    Attributes:
        root: 根节点
        current_section: 当前节以你
        current_subsection: 当前子节
        current_numbered_section: 当前编号节
        batch_number: 批次号
    """

    def __init__(self) -> None:
        """初始化文档结构"""
        self.root = DocumentNode("文档结构", 0, "root")
        self.current_section: Optional[DocumentNode] = None
        self.current_subsection: Optional[DocumentNode] = None
        self.current_numbered_section: Optional[DocumentNode] = None
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
            content: 节点内容，可选
            level: 节点层级，可选
            metadata: 元数据，可选
            parent_node: 父节点，可选

        Returns:
            添加的节点
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
            self.current_section = node
            self.current_subsection = None
            self.current_numbered_section = None
        elif level == 2:
            if self.current_section:
                self.current_section.children.append(node)
                self.current_subsection = node
                self.current_numbered_section = None
            else:
                self.root.children.append(node)
                self.current_subsection = node
        elif level == 3:
            if self.current_subsection:
                self.current_subsection.children.append(node)
                self.current_numbered_section = node
            elif self.current_section:
                self.current_section.children.append(node)
                self.current_numbered_section = node
            else:
                self.root.children.append(node)
        else:
            if self.current_numbered_section:
                self.current_numbered_section.children.append(node)
            elif self.current_subsection:
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
            文档结构的字典表示
        """
        return self.root.to_dict()

    def find_nodes_by_type(self, node_type: str) -> List[DocumentNode]:
        """
        根据节点类型查找节点

        Args:
            node_type: 要查找的节点类型

        Returns:
            匹配的节点列表
        """
        return self.root.find_by_type(node_type)

    def find_node_by_title(self, title: str) -> Optional[DocumentNode]:
        """
        根据标题查找节点

        Args:
            title: 要查找的标题

        Returns:
            匹配的节点，如果未找到则返回None
        """
        return self.root.find_by_title(title)
