"""
自定义异常模块
"""

from doc_processor.exceptions.exceptions import (
    ConfigurationError,
    DocProcessorError,
    DocumentError,
    ExtractionError,
    ProcessingError,
    ValidationError,
)

__all__ = [
    "DocProcessorError",
    "ConfigurationError",
    "ProcessingError",
    "DocumentError",
    "ExtractionError",
    "ValidationError",
]
