"""
文本处理工具模块
"""

import re
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

# 预编译正则表达式
WHITESPACE_PATTERN = re.compile(r"\s+")
COUNT_PATTERN = re.compile(r"(共计|总计|合计).*?(\d+).*?(款|个|种|辆|台|项)")


@lru_cache(maxsize=1024)
def clean_text(text: str) -> str:
    """
    清理文本内容，使用缓存提高性能

    Args:
        text: 待清理的文本

    Returns:
        清理后的文本
    """
    # 移除多余的空白字符
    text = WHITESPACE_PATTERN.sub(" ", text.strip())
    # 统一全角字符到半角
    text = text.replace("，", ",").replace("；", ";")
    return text


def extract_count_from_text(text: str) -> Optional[int]:
    """
    从文本中提取数量信息

    Args:
        text: 待提取的文本

    Returns:
        提取的数量，如果未找到则返回None
    """
    match = COUNT_PATTERN.search(text)
    if match:
        try:
            return int(match.group(2))
        except (ValueError, IndexError):
            pass
    return None


def validate_car_info(
    car_info: Dict[str, Any],
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    验证并尝试修复车辆信息

    Args:
        car_info: 车辆信息字典

    Returns:
        验证结果元组：(是否有效, 错误信息, 修复后的信息)
    """
    # 基本验证
    if not car_info or not any(str(value).strip() for value in car_info.values()):
        return False, "空行", None

    # 检查是否为合计行
    if any(
        str(value).strip().startswith(("合计", "总计")) for value in car_info.values()
    ):
        return False, "合计行", None

    # 尝试修复数据
    fixed_info = car_info.copy()

    # 1. 处理变速器信息
    if "型式" in fixed_info and "档位数" in fixed_info:
        fixed_info["变速器"] = f"{fixed_info.pop('型式')} {fixed_info.pop('档位数')}"

    # 2. 标准化数值字段
    numeric_fields = ["排量(ml)", "整车整备质量(kg)", "综合燃料消耗量（L/100km）"]
    for field in numeric_fields:
        if field in fixed_info:
            value = fixed_info[field]
            if isinstance(value, str):
                # 处理多个数值的情况（如范围值）
                if "/" in value:
                    values = [float(v.strip()) for v in value.split("/") if v.strip()]
                    if values:
                        fixed_info[field] = min(values)  # 使用最小值
                else:
                    try:
                        fixed_info[field] = float(value.replace("，", ","))
                    except ValueError:
                        pass

    # 3. 确保必要字段存在
    required_fields = ["car_type", "category", "sub_type"]
    for field in required_fields:
        if field not in fixed_info:
            return False, f"缺少必要字段: {field}", None

    return True, "", fixed_info


def process_car_info(
    car_info: Dict[str, Any], batch_number: Optional[str] = None
) -> Dict[str, Any]:
    """
    处理车辆信息，合并和标准化字段

    Args:
        car_info: 原始车辆信息字典
        batch_number: 批次号

    Returns:
        处理后的车辆信息字典
    """
    # 添加批次号
    if batch_number:
        car_info["batch"] = batch_number

    # 合并型号字段
    model_fields = ["产品型号", "车辆型号", "型号"]
    model_values = []
    for field in model_fields:
        if field in car_info:
            value = car_info.pop(field) if field != "型号" else car_info.get(field)
            if value and str(value).strip():
                model_values.append(clean_text(str(value)))

    if model_values:
        car_info["型号"] = model_values[0]  # 使用第一个非空的型号

    # 标准化字段名称
    field_mapping = {
        "通用名称": "品牌",
        "商标": "品牌",
        "生产企业": "企业名称",
        "企业": "企业名称",
    }

    # 处理字段映射
    for old_field, new_field in field_mapping.items():
        if old_field in car_info:
            value = car_info.pop(old_field)
            if value and str(value).strip():
                car_info[new_field] = clean_text(str(value))

    # 清理其他字段的文本，但保留所有值
    for key in car_info:
        if isinstance(car_info[key], str):
            car_info[key] = clean_text(car_info[key])

    return car_info
