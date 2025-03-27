"""
核心模块，包含文档处理的主要逻辑
"""

from doc_processor.core.exporter import DataExporter
from doc_processor.core.processor import DocProcessor

__all__ = ["DocProcessor", "DataExporter"]
