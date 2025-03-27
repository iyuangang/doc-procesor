"""
自定义异常类模块
"""

from typing import Any, Optional


class DocProcessorError(Exception):
    """文档处理器的基础异常类"""

    def __init__(self, message: str, *args: Any) -> None:
        self.message = message
        super().__init__(message, *args)


class ConfigurationError(DocProcessorError):
    """配置错误异常"""

    def __init__(self, message: str, config_file: Optional[str] = None) -> None:
        self.config_file = config_file
        super_message = f"{message}" + (
            f" (配置文件: {config_file})" if config_file else ""
        )
        super().__init__(super_message)


class ProcessingError(DocProcessorError):
    """处理错误异常"""

    def __init__(self, message: str, doc_path: Optional[str] = None) -> None:
        self.doc_path = doc_path
        super_message = f"{message}" + (f" (文档: {doc_path})" if doc_path else "")
        super().__init__(super_message)


class DocumentError(DocProcessorError):
    """文档错误异常"""

    def __init__(self, message: str, doc_path: Optional[str] = None) -> None:
        self.doc_path = doc_path
        super_message = f"{message}" + (f" (文档: {doc_path})" if doc_path else "")
        super().__init__(super_message)


class ExtractionError(DocProcessorError):
    """提取错误异常"""

    def __init__(
        self,
        message: str,
        doc_path: Optional[str] = None,
        element_type: Optional[str] = None,
    ) -> None:
        self.doc_path = doc_path
        self.element_type = element_type
        super_message = f"{message}"
        if doc_path:
            super_message += f" (文档: {doc_path})"
        if element_type:
            super_message += f" (元素类型: {element_type})"
        super().__init__(super_message)


class ValidationError(DocProcessorError):
    """验证错误异常"""

    def __init__(self, message: str, data: Optional[Any] = None) -> None:
        self.data = data
        super_message = f"{message}"
        if data:
            super_message += (
                f" (数据: {str(data)[:100]}...)"
                if len(str(data)) > 100
                else f" (数据: {data})"
            )
        super().__init__(super_message)
