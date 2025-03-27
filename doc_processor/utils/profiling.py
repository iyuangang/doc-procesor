"""
性能分析工具模块
"""

import cProfile
import functools
import os
import pstats
import time
from io import StringIO
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast

import psutil

from doc_processor.utils.logging_utils import create_logger

# 创建日志记录器
logger = create_logger(__name__)

# 类型变量定义
F = TypeVar("F", bound=Callable[..., Any])


def profile_function(func: F) -> F:
    """
    函数性能分析装饰器

    Args:
        func: 要分析的函数

    Returns:
        装饰后的函数
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        profile = cProfile.Profile()
        try:
            return profile.runcall(func, *args, **kwargs)
        finally:
            s = StringIO()
            stats = pstats.Stats(profile, stream=s).sort_stats("cumulative")
            stats.print_stats(20)  # 显示前20个最耗时的函数调用
            logger.debug(f"性能分析报告 ({func.__name__}):\n{s.getvalue()}")

    return cast(F, wrapper)


def time_function(func: F) -> F:
    """
    函数执行时间测量装饰器

    Args:
        func: 要测量的函数

    Returns:
        装饰后的函数
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed_time = time.time() - start_time
        logger.debug(f"函数 {func.__name__} 执行时间: {elapsed_time:.3f} 秒")
        return result

    return cast(F, wrapper)


def get_memory_usage() -> str:
    """
    获取当前进程的内存使用情况

    Returns:
        内存使用信息字符串
    """
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return f"{memory_info.rss / 1024 / 1024:.1f}MB"


class TimingContext:
    """执行时间上下文管理器"""

    def __init__(self, name: str, verbose: bool = True) -> None:
        """
        初始化上下文管理器

        Args:
            name: 操作名称
            verbose: 是否显示详细信息
        """
        self.name = name
        self.verbose = verbose
        self.start_time = 0.0
        self.timing_data: Dict[str, float] = {}

    def __enter__(self) -> "TimingContext":
        """
        进入上下文管理器

        Returns:
            上下文管理器实例
        """
        self.start_time = time.time()
        if self.verbose:
            logger.debug(f"开始执行 {self.name}")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        退出上下文管理器

        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常跟踪
        """
        elapsed = time.time() - self.start_time
        self.timing_data[self.name] = elapsed
        if self.verbose:
            logger.debug(f"{self.name} 执行完成，耗时: {elapsed:.3f} 秒")
            logger.debug(f"当前内存使用: {get_memory_usage()}")

    def log_step(self, step_name: str) -> None:
        """
        记录单个步骤的执行时间

        Args:
            step_name: 步骤名称
        """
        current_time = time.time()
        elapsed = current_time - self.start_time
        self.timing_data[step_name] = elapsed
        if self.verbose:
            logger.debug(f"步骤 {step_name} 耗时: {elapsed:.3f} 秒")
        self.start_time = current_time

    def get_summary(self) -> List[str]:
        """
        获取时间统计摘要

        Returns:
            时间统计信息列表
        """
        if not self.timing_data:
            return ["没有可用的时间数据"]

        sorted_items = sorted(self.timing_data.items(), key=lambda x: x[1])
        total_time = sum(self.timing_data.values())
        summary = [f"总执行时间: {total_time:.3f} 秒"]

        for name, elapsed in sorted_items:
            percentage = elapsed / total_time * 100 if total_time > 0 else 0
            summary.append(f"{name}: {elapsed:.3f} 秒 ({percentage:.1f}%)")

        return summary
