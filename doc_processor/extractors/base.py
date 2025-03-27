"""
提取器基类模块
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, List, Optional, TypeVar

from doc_processor.utils import TimingContext, create_logger

# 创建日志记录器
logger = create_logger(__name__)

# 泛型类型变量
T = TypeVar("T")


class BaseExtractor(Generic[T], ABC):
    """
    提取器基类

    Attributes:
        name: 提取器名称
        verbose: 是否显示详细信息
    """

    def __init__(self, name: str, verbose: bool = False) -> None:
        """
        初始化提取器

        Args:
            name: 提取器名称
            verbose: 是否显示详细信息
        """
        self.name = name
        self.verbose = verbose
        self.timing_context = TimingContext(name, verbose=verbose)

    @abstractmethod
    def extract(self) -> T:
        """
        提取信息

        Returns:
            提取的信息
        """
        pass

    def log_info(self, message: str) -> None:
        """
        记录信息日志

        Args:
            message: 日志消息
        """
        if self.verbose:
            logger.info(f"[{self.name}] {message}")
        else:
            logger.debug(f"[{self.name}] {message}")

    def log_error(self, message: str) -> None:
        """
        记录错误日志

        Args:
            message: 日志消息
        """
        logger.error(f"[{self.name}] {message}")

    def log_warning(self, message: str) -> None:
        """
        记录警告日志

        Args:
            message: 日志消息
        """
        logger.warning(f"[{self.name}] {message}")

    def log_step(self, step_name: str) -> None:
        """
        记录步骤耗时

        Args:
            step_name: 步骤名称
        """
        self.timing_context.log_step(step_name)

    def __enter__(self) -> "BaseExtractor[T]":
        """
        进入上下文

        Returns:
            提取器实例
        """
        self.timing_context.__enter__()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        退出上下文

        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常跟踪
        """
        self.timing_context.__exit__(exc_type, exc_val, exc_tb)
