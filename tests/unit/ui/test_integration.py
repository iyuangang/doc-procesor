"""
UI模块集成测试
测试UI组件与其他模块的交互
"""

import json
import os
import io
import pytest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path

from rich.console import Console

from src.ui.console import display_summary_dashboard
from src.batch.validator import (
    calculate_statistics,
    verify_batch_consistency,
    verify_all_batches,
)
from src.processor.doc_processor import DocProcessor


class TestUIIntegration:
    """测试UI与其他模块的集成"""

    @pytest.fixture
    def mock_console(self):
        """创建模拟控制台"""
        string_io = io.StringIO()
        console = Console(file=string_io, width=120, height=60)

        with patch("src.ui.console.console", console):
            yield string_io

    @pytest.fixture
    def test_data(self):
        """加载测试数据"""
        test_data_file = (
            Path(__file__).parent.parent.parent / "test_data" / "mock_batch_data.json"
        )
        with open(test_data_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def test_integration_with_batch_validator(self, mock_console, test_data):
        """测试与批次验证模块的集成"""
        # 获取测试数据
        cars = test_data["cars"]

        # 使用批次验证模块计算统计信息
        stats = calculate_statistics(cars)

        # 进行批次一致性验证
        consistency_result = verify_batch_consistency(
            cars, batch_number="1", declared_count=5
        )

        # 验证所有批次
        batch_results = verify_all_batches(cars)

        # 使用仪表盘显示结果
        with patch("time.strftime", return_value="2025-05-23 16:00:00"):
            display_summary_dashboard(
                cars, batch_results, consistency_result, "test_output.csv"
            )

        # 获取输出
        output = mock_console.getvalue()

        # 验证输出包含从批次验证模块获取的信息
        assert "车辆数据处理结果汇总" in output
        assert "共处理 5 条记录" in output
        assert f"节能型汽车" in output and f"{stats['energy_saving_count']}" in output
        assert f"新能源汽车" in output and f"{stats['new_energy_count']}" in output
        assert "批次分布" in output
        assert "第1批" in output
        assert "第2批" in output

    def test_integration_with_processor(self, mock_console, test_data, monkeypatch):
        """测试与处理器模块的集成"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # 模拟DocProcessor处理结果
            mock_processor = MagicMock(spec=DocProcessor)
            mock_processor.cars = test_data["cars"]
            mock_processor.doc_path = "mock_doc.docx"
            mock_processor.batch_number = "1"

            # 模拟_get_config方法
            def mock_get_config(key, default):
                if key == "output.use_dashboard":
                    return True
                return default

            mock_processor._get_config.side_effect = mock_get_config

            # 模拟verify_all_batches函数
            def mock_verify_all_batches(*args, **kwargs):
                return test_data["batch_results"]

            # 模拟verify_batch_consistency函数
            def mock_verify_batch_consistency(*args, **kwargs):
                return test_data["consistency_results"]["match"]

            # 应用补丁
            monkeypatch.setattr(
                "src.batch.validator.verify_all_batches", mock_verify_all_batches
            )
            monkeypatch.setattr(
                "src.batch.validator.verify_batch_consistency",
                mock_verify_batch_consistency,
            )

            # 模拟时间
            with patch("time.strftime", return_value="2025-05-23 16:00:00"):
                # 直接调用display_summary_dashboard
                display_summary_dashboard(
                    mock_processor.cars,
                    test_data["batch_results"],
                    test_data["consistency_results"]["match"],
                    tmp_path,
                )

            # 获取输出
            output = mock_console.getvalue()

            # 验证输出
            assert "车辆数据处理结果汇总" in output
            assert "共处理 5 条记录" in output
            assert "节能型汽车" in output and "2" in output  # 2条节能型记录
            assert "新能源汽车" in output and "3" in output  # 3条新能源记录
            assert "批次分布" in output
            assert "第1批" in output
            assert "第2批" in output
            assert "数据一致" in output

            # 验证输出文件信息存在，但不检查具体路径
            assert "输出文件:" in output

        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_dashboard_different_data_scenarios(self, mock_console, test_data):
        """测试仪表盘在不同数据场景下的表现"""
        cars = test_data["cars"]

        scenarios = [
            # 场景1: 匹配数据
            {
                "name": "match",
                "consistency": test_data["consistency_results"]["match"],
                "expected": ["数据一致", "第1批"],
            },
            # 场景2: 不匹配数据
            {
                "name": "mismatch",
                "consistency": test_data["consistency_results"]["mismatch"],
                "expected": ["数据不一致", "期望记录: 10", "实际记录: 5"],
            },
            # 场景3: 无批次数据
            {
                "name": "no_batch",
                "consistency": test_data["consistency_results"]["no_batch"],
                "expected": ["未知状态", "批次: 共2批"],
            },
        ]

        for scenario in scenarios:
            # 清除之前的输出
            mock_console.seek(0)
            mock_console.truncate(0)

            # 使用仪表盘显示
            with patch("time.strftime", return_value="2025-05-23 16:00:00"):
                display_summary_dashboard(
                    cars,
                    test_data["batch_results"],
                    scenario["consistency"],
                    f"output_{scenario['name']}.csv",
                )

            # 获取输出
            output = mock_console.getvalue()

            # 验证期望输出存在
            for expected_text in scenario["expected"]:
                assert (
                    expected_text in output
                ), f"场景 '{scenario['name']}' 缺少预期文本: '{expected_text}'"
