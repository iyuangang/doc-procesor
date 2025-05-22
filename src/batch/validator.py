"""
批次验证模块 - 提供批次数据验证功能
"""

from typing import Dict, Any, List, Optional

from ..models.car_info import CarInfo


def verify_batch_consistency(
    cars: List[Dict[str, Any]],
    batch_number: Optional[str],
    declared_count: Optional[int] = None,
) -> Dict[str, Any]:
    """
    验证每个批次的表格数据总和是否与批次总记录数一致
    即便没有声明的总记录数，也验证表格记录数与处理后的记录数是否一致

    Args:
        cars: 车辆信息列表
        batch_number: 批次号
        declared_count: 声明的总记录数

    Returns:
        包含批次验证结果的字典
    """
    # 如果没有批次号，直接返回
    if not batch_number:
        return {"status": "no_batch", "message": "未找到批次号"}

    # 按表格分组统计车辆记录数
    table_counts: Dict[Any, int] = {}
    for car in cars:
        table_id = car.get("table_id", "未知")
        if table_id not in table_counts:
            table_counts[table_id] = 0
        table_counts[table_id] += 1

    # 计算从表格中提取的总记录数
    total_extracted_count = sum(table_counts.values())

    # 验证结果
    if declared_count is not None:
        # 如果有声明的总记录数，比较声明数与实际数
        if total_extracted_count == declared_count:
            return {
                "status": "match",
                "message": f"批次记录数匹配：声明 {declared_count}, 实际 {total_extracted_count}",
                "batch": batch_number,
                "actual_count": total_extracted_count,
                "declared_count": declared_count,
                "table_counts": table_counts,
            }
        else:
            return {
                "status": "mismatch",
                "message": f"批次记录数不匹配：声明 {declared_count}, 实际 {total_extracted_count}",
                "batch": batch_number,
                "actual_count": total_extracted_count,
                "declared_count": declared_count,
                "table_counts": table_counts,
                "difference": declared_count - total_extracted_count,
            }
    else:
        # 如果没有声明的总记录数，验证表格总记录数与处理后的记录数是否一致
        processed_count = len(cars)
        if total_extracted_count == processed_count:
            return {
                "status": "internal_match",
                "message": f"内部一致性检查通过：表格记录总数 {total_extracted_count} 与处理结果数 {processed_count} 一致",
                "batch": batch_number,
                "actual_count": total_extracted_count,
                "processed_count": processed_count,
                "table_counts": table_counts,
            }
        else:
            return {
                "status": "internal_mismatch",
                "message": f"内部一致性检查失败：表格记录总数 {total_extracted_count} 与处理结果数 {processed_count} 不一致",
                "batch": batch_number,
                "actual_count": total_extracted_count,
                "processed_count": processed_count,
                "table_counts": table_counts,
                "difference": total_extracted_count - processed_count,
            }


def verify_all_batches(all_cars_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    验证所有批次的数据一致性

    Args:
        all_cars_data: 所有车辆信息列表

    Returns:
        包含所有批次验证结果的字典
    """
    # 按批次分组
    batch_data: Dict[str, List[Dict[str, Any]]] = {}
    for car in all_cars_data:
        batch = car.get("batch")
        if not batch:
            continue

        if batch not in batch_data:
            batch_data[batch] = []
        batch_data[batch].append(car)

    # 验证每个批次
    results = {}
    for batch, cars in batch_data.items():
        # 按表格分组
        table_counts = {}
        for car in cars:
            table_id = car.get("table_id", "未知")
            if table_id not in table_counts:
                table_counts[table_id] = 0
            table_counts[table_id] += 1

        # 总计
        total_count = len(cars)

        results[batch] = {"total": total_count, "table_counts": table_counts}

    return results


def find_duplicated_models(cars: List[Dict[str, Any]]) -> List[str]:
    """
    查找重复的车辆型号

    Args:
        cars: 车辆信息列表

    Returns:
        重复的车辆型号列表
    """
    model_counts: Dict[str, int] = {}

    # 统计每个型号的出现次数
    for car in cars:
        model = car.get("vmodel")
        if not model:
            continue

        if model not in model_counts:
            model_counts[model] = 0
        model_counts[model] += 1

    # 返回出现次数大于1的型号
    return [model for model, count in model_counts.items() if count > 1]


def calculate_statistics(cars: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    计算车辆数据统计信息

    Args:
        cars: 车辆信息列表

    Returns:
        包含统计信息的字典
    """
    total_count = len(cars)

    # 统计节能型和新能源汽车数量
    energy_saving_count = sum(1 for car in cars if car.get("energytype") == 2)
    new_energy_count = sum(1 for car in cars if car.get("energytype") == 1)

    # 统计各批次数量
    batch_counts: Dict[str, int] = {}
    for car in cars:
        batch = car.get("batch", "未知")
        if batch not in batch_counts:
            batch_counts[batch] = 0
        batch_counts[batch] += 1

    # 统计各类型数量
    category_counts: Dict[str, int] = {}
    for car in cars:
        category = car.get("category", "未知")
        if category not in category_counts:
            category_counts[category] = 0
        category_counts[category] += 1

    # 统计各子类型数量
    subtype_counts: Dict[str, int] = {}
    for car in cars:
        subtype = car.get("sub_type", "未知")
        if subtype not in subtype_counts:
            subtype_counts[subtype] = 0
        subtype_counts[subtype] += 1

    return {
        "total_count": total_count,
        "energy_saving_count": energy_saving_count,
        "new_energy_count": new_energy_count,
        "batch_counts": batch_counts,
        "category_counts": category_counts,
        "subtype_counts": subtype_counts,
    }
