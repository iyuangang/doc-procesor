"""
文本处理模块 - 提供文本清理、格式化等功能
"""

import re
from functools import lru_cache
from typing import Pattern

# 预编译正则表达式
WHITESPACE_PATTERN: Pattern[str] = re.compile(r"\s+")


@lru_cache(maxsize=1024)
def clean_text(text: str) -> str:
    """
    清理文本内容，使用缓存提高性能

    Args:
        text: 需要清理的文本

    Returns:
        清理后的文本
    """
    # 移除多余的空白字符
    text = WHITESPACE_PATTERN.sub(" ", text.strip())
    # 统一全角字符到半角
    text = text.replace("，", ", ").replace("；", "; ")
    return text
