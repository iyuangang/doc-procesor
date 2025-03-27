"""
中文数字工具模块，提供中文数字转阿拉伯数字的功能
"""

import re
from functools import lru_cache
from typing import Dict, Optional

# 中文数字映射表
CN_NUMS: Dict[str, str] = {
    "零": "0",
    "一": "1",
    "二": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
    "十": "10",
    "百": "100",
}

# 预编译正则表达式
BATCH_NUMBER_PATTERN = re.compile(r"第([一二三四五六七八九十百零\d]+)批")
CHINESE_NUMBER_PATTERN = re.compile(r"([一二三四五六七八九十百零]+)")


@lru_cache(maxsize=1024)
def cn_to_arabic(cn_num: str) -> str:
    """
    将中文数字转换为阿拉伯数字，使用缓存提高性能

    Args:
        cn_num: 中文数字字符串

    Returns:
        阿拉伯数字字符串
    """
    if cn_num.isdigit():
        return cn_num

    # 处理个位数
    if len(cn_num) == 1:
        return CN_NUMS.get(cn_num, cn_num)

    # 处理"百"开头的数字
    if "百" in cn_num:
        parts = cn_num.split("百")
        hundreds = int(CN_NUMS[parts[0]])
        if not parts[1]:  # 整百
            return str(hundreds * 100)
        # 处理带"零"的情况
        if parts[1].startswith("零"):
            ones = int(CN_NUMS[parts[1][-1]])
            return str(hundreds * 100 + ones)
        return str(hundreds * 100 + int(cn_to_arabic(parts[1])))

    # 处理"十"开头的数字
    if cn_num.startswith("十"):
        if len(cn_num) == 1:
            return "10"
        return "1" + CN_NUMS[cn_num[1]]

    # 处理带十的两位数
    if "十" in cn_num:
        parts = cn_num.split("十")
        # 直接在字符串格式化中使用CN_NUMS字典的值，避免类型转换
        if len(parts) == 1 or not parts[1]:
            return f"{CN_NUMS[parts[0]]}0"
        return f"{CN_NUMS[parts[0]]}{CN_NUMS[parts[1]]}"

    return CN_NUMS.get(cn_num, cn_num)


@lru_cache(maxsize=1024)
def extract_batch_number(text: str) -> Optional[str]:
    """
    从文本中提取批次号，使用缓存提高性能

    Args:
        text: 待提取的文本

    Returns:
        批次号，如果未找到则返回None
    """
    # 先尝试匹配完整的批次号格式
    match = BATCH_NUMBER_PATTERN.search(text)
    if match:
        num = match.group(1)
        # 如果是纯数字，直接返回
        if num.isdigit():
            return num

        # 转换中文数字
        try:
            return cn_to_arabic(num)
        except (KeyError, ValueError):
            return None

    # 如果没有找到批次号格式，尝试直接转换纯中文数字
    if any(char in text for char in "一二三四五六七八九十百零"):
        try:
            # 提取连续的中文数字
            match = CHINESE_NUMBER_PATTERN.search(text)
            if match:
                return cn_to_arabic(match.group(1))
        except (KeyError, ValueError):
            pass

    return None
