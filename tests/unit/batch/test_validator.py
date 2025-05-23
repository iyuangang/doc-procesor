"""
测试批次验证模块
"""

import pytest
from src.batch.validator import (
    verify_batch_consistency,
    verify_all_batches,
    find_duplicated_models,
    calculate_statistics,
)
from src.models.car_info import CarInfo


# 测试数据
@pytest.fixture
def sample_cars():
    """创建测试用的车辆数据样本"""
    return [
        {
            "vmodel": "Model A",
            "category": "轿车",
            "sub_type": "小型车",
            "batch": "B001",
            "energytype": 1,  # 新能源
            "企业名称": "Company X",
            "品牌": "Brand X",
            "table_id": 1,
            "raw_text": "Sample text 1",
        },
        {
            "vmodel": "Model B",
            "category": "轿车",
            "sub_type": "中型车",
            "batch": "B001",
            "energytype": 2,  # 节能型
            "企业名称": "Company X",
            "品牌": "Brand Y",
            "table_id": 1,
            "raw_text": "Sample text 2",
        },
        {
            "vmodel": "Model A",  # 重复型号
            "category": "SUV",
            "sub_type": "大型车",
            "batch": "B002",
            "energytype": 1,  # 新能源
            "企业名称": "Company Y",
            "品牌": "Brand Z",
            "table_id": 2,
            "raw_text": "Sample text 3",
        },
    ]


def test_verify_batch_consistency_match(sample_cars):
    """测试批次一致性验证 - 匹配情况"""
    # 过滤出B001批次的车辆
    b001_cars = [car for car in sample_cars if car["batch"] == "B001"]

    # 验证声明数量与实际数量一致的情况
    result = verify_batch_consistency(b001_cars, "B001", 2)

    assert result["status"] == "match"
    assert result["actual_count"] == 2
    assert result["declared_count"] == 2
    assert result["batch"] == "B001"
    assert "table_counts" in result


def test_verify_batch_consistency_mismatch(sample_cars):
    """测试批次一致性验证 - 不匹配情况"""
    # 过滤出B001批次的车辆
    b001_cars = [car for car in sample_cars if car["batch"] == "B001"]

    # 验证声明数量与实际数量不一致的情况
    result = verify_batch_consistency(b001_cars, "B001", 3)

    assert result["status"] == "mismatch"
    assert result["actual_count"] == 2
    assert result["declared_count"] == 3
    assert result["difference"] == 1
    assert result["batch"] == "B001"


def test_verify_batch_consistency_internal_match(sample_cars):
    """测试批次内部一致性验证 - 匹配情况"""
    # 过滤出B001批次的车辆
    b001_cars = [car for car in sample_cars if car["batch"] == "B001"]

    # 验证内部一致性（不提供声明数量）
    result = verify_batch_consistency(b001_cars, "B001")

    assert result["status"] == "internal_match"
    assert result["actual_count"] == 2
    assert result["processed_count"] == 2
    assert result["batch"] == "B001"


def test_verify_batch_consistency_no_batch(sample_cars):
    """测试批次一致性验证 - 无批次号情况"""
    result = verify_batch_consistency(sample_cars, None)

    assert result["status"] == "no_batch"
    assert result["message"] == "未找到批次号"


def test_verify_all_batches(sample_cars):
    """测试验证所有批次"""
    result = verify_all_batches(sample_cars)

    assert "B001" in result
    assert "B002" in result
    assert result["B001"]["total"] == 2
    assert result["B002"]["total"] == 1
    assert result["B001"]["table_counts"][1] == 2
    assert result["B002"]["table_counts"][2] == 1


def test_find_duplicated_models(sample_cars):
    """测试查找重复的车辆型号"""
    duplicates = find_duplicated_models(sample_cars)

    assert len(duplicates) == 1
    assert "Model A" in duplicates


def test_calculate_statistics(sample_cars):
    """测试计算统计信息"""
    stats = calculate_statistics(sample_cars)

    assert stats["total_count"] == 3
    assert stats["energy_saving_count"] == 1
    assert stats["new_energy_count"] == 2
    assert stats["batch_counts"]["B001"] == 2
    assert stats["batch_counts"]["B002"] == 1
    assert stats["category_counts"]["轿车"] == 2
    assert stats["category_counts"]["SUV"] == 1
    assert stats["subtype_counts"]["小型车"] == 1
    assert stats["subtype_counts"]["中型车"] == 1
    assert stats["subtype_counts"]["大型车"] == 1
