"""
控制台显示模块测试
"""

import io
import os
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import time
from typing import Dict, Any, List

import pandas as pd
from rich.console import Console

from src.ui.console import (
    display_statistics,
    display_batch_verification,
    display_consistency_result,
    display_summary_dashboard,
    generate_ascii_bar_chart,
    generate_spark_line,
)


class TestAsciiCharts:
    """测试ASCII图表生成功能"""

    @pytest.fixture
    def mock_console_output(self):
        """模拟控制台输出的fixture"""
        string_io = io.StringIO()
        console = Console(file=string_io, width=100, height=30)

        with patch("src.ui.console.console", console):
            yield string_io

    def test_generate_ascii_bar_chart(self, mock_console_output):
        """测试柱状图生成"""
        # 准备测试数据
        data = {"A": 10, "B": 5, "C": 1}

        # 生成图表并打印
        panel = generate_ascii_bar_chart(data, "测试图表", width=20)
        Console(file=mock_console_output).print(panel)

        # 获取输出
        output = mock_console_output.getvalue()

        # 验证图表包含所有数据点
        assert "测试图表" in output
        assert "A" in output and "10" in output
        assert "B" in output and "5" in output
        assert "C" in output and "1" in output

        # 验证柱长度关系：A应该有更多的方块字符
        assert output.count("█") > 0

    def test_generate_ascii_bar_chart_empty_data(self, mock_console_output):
        """测试空数据情况"""
        panel = generate_ascii_bar_chart({}, "空图表")
        Console(file=mock_console_output).print(panel)

        output = mock_console_output.getvalue()
        assert "空图表" in output
        assert "没有数据可显示" in output

    def test_generate_spark_line(self, mock_console_output):
        """测试折线图生成"""
        # 准备测试数据
        data = [1, 3, 2, 5, 4]

        # 生成图表并打印
        panel = generate_spark_line(data, "测试折线图")
        Console(file=mock_console_output).print(panel)

        # 获取输出
        output = mock_console_output.getvalue()

        # 验证图表包含信息
        assert "测试折线图" in output
        assert "最小值: 1" in output
        assert "最大值: 5" in output
        assert "平均值: 3.0" in output

        # 验证包含spark line字符
        assert any(c in output for c in "▁▂▃▄▅▆▇█")

    def test_generate_spark_line_empty_data(self, mock_console_output):
        """测试空数据情况"""
        panel = generate_spark_line([], "空折线图")
        Console(file=mock_console_output).print(panel)

        output = mock_console_output.getvalue()
        assert "空折线图" in output
        assert "没有数据可显示" in output


class TestDashboard:
    """测试仪表盘显示功能"""

    @pytest.fixture
    def mock_console_output(self):
        """模拟控制台输出的fixture"""
        string_io = io.StringIO()
        console = Console(file=string_io, width=100, height=30)

        with patch("src.ui.console.console", console):
            yield string_io

    @pytest.fixture
    def sample_car_data(self):
        """生成样本车辆数据"""
        cars = []
        # 节能型汽车
        for i in range(10):
            cars.append(
                {
                    "energytype": 2,
                    "vmodel": f"节能型车型{i}",
                    "category": "节能型",
                    "batch": "1",
                    "table_id": 1,
                }
            )

        # 新能源汽车
        for i in range(5):
            cars.append(
                {
                    "energytype": 1,
                    "vmodel": f"新能源车型{i}",
                    "category": "新能源",
                    "batch": "2",
                    "table_id": 2,
                }
            )

        return cars

    @pytest.fixture
    def sample_batch_results(self):
        """生成样本批次验证结果"""
        return {
            "1": {"total": 10, "table_counts": {1: 10}},
            "2": {"total": 5, "table_counts": {2: 5}},
        }

    @pytest.fixture
    def sample_consistency_result(self):
        """生成样本一致性检查结果"""
        return {
            "status": "match",
            "message": "批次记录数匹配：声明 15, 实际 15",
            "batch": "1",
            "actual_count": 15,
            "declared_count": 15,
            "table_counts": {1: 10, 2: 5},
        }

    def test_display_statistics(self, mock_console_output):
        """测试统计信息显示"""
        # 调用函数
        display_statistics(100, 60, 40, "output.csv")

        # 获取输出
        output = mock_console_output.getvalue()

        # 验证输出内容
        assert "处理统计报告" in output
        assert "总记录数" in output and "100" in output
        assert "节能型汽车" in output and "60" in output
        assert "新能源汽车" in output and "40" in output
        assert "60.0%" in output  # 60/100 = 60%
        assert "40.0%" in output  # 40/100 = 40%
        assert "output.csv" in output

    def test_display_batch_verification(
        self, mock_console_output, sample_batch_results
    ):
        """测试批次验证结果显示"""
        # 调用函数
        display_batch_verification(sample_batch_results)

        # 获取输出
        output = mock_console_output.getvalue()

        # 验证输出内容
        assert "批次数据汇总" in output
        assert "第1批" in output and "10" in output
        assert "第2批" in output and "5" in output

    def test_display_consistency_result_match(self, mock_console_output):
        """测试一致性检查结果显示 - 匹配情况"""
        # 准备测试数据
        result = {
            "status": "match",
            "message": "批次记录数匹配：声明 100, 实际 100",
            "batch": "1",
            "actual_count": 100,
            "declared_count": 100,
        }

        # 调用函数
        display_consistency_result(result)

        # 获取输出
        output = mock_console_output.getvalue()

        # 验证输出内容
        assert "数据一致性检查" in output
        assert "记录数匹配" in output
        assert "第1批" in output
        assert "100" in output

    def test_display_consistency_result_mismatch(self, mock_console_output):
        """测试一致性检查结果显示 - 不匹配情况"""
        # 准备测试数据
        result = {
            "status": "mismatch",
            "message": "批次记录数不匹配：声明 100, 实际 90",
            "batch": "1",
            "actual_count": 90,
            "declared_count": 100,
            "difference": 10,
        }

        # 调用函数
        display_consistency_result(result)

        # 获取输出
        output = mock_console_output.getvalue()

        # 验证输出内容
        assert "数据一致性检查" in output
        assert "记录数不匹配" in output
        assert "第1批" in output
        assert "声明 100" in output
        assert "实际 90" in output
        assert "差异 10" in output

    def test_display_summary_dashboard(
        self,
        mock_console_output,
        sample_car_data,
        sample_batch_results,
        sample_consistency_result,
    ):
        """测试仪表盘显示功能"""
        # 模拟时间
        with patch("time.strftime", return_value="2025-05-23 16:00:00"):
            # 调用函数
            display_summary_dashboard(
                sample_car_data,
                sample_batch_results,
                sample_consistency_result,
                "output.csv",
            )

        # 获取输出
        output = mock_console_output.getvalue()

        # 验证输出内容
        assert "车辆数据处理结果汇总" in output
        assert "共处理 15 条记录" in output
        assert "节能型汽车" in output and "10" in output
        assert "新能源汽车" in output and "5" in output
        assert "数据统计" in output
        assert "批次分布" in output
        assert "第1批" in output
        assert "第2批" in output
        assert "一致性检查:" in output
        assert "数据一致" in output
        assert "实际记录: 15" in output
        assert "输出文件:" in output and "output.csv" in output

    def test_display_summary_dashboard_many_batches(self, mock_console_output):
        """测试多批次情况下的仪表盘显示"""
        # 准备大量批次数据
        cars = []
        batch_results = {}

        # 创建25个批次
        for batch in range(1, 26):
            batch_name = str(batch)
            # 每个批次10条记录
            for i in range(10):
                cars.append(
                    {
                        "energytype": 2 if batch % 2 == 0 else 1,
                        "vmodel": f"车型_{batch}_{i}",
                        "category": "节能型" if batch % 2 == 0 else "新能源",
                        "batch": batch_name,
                        "table_id": batch,
                    }
                )

            batch_results[batch_name] = {"total": 10, "table_counts": {batch: 10}}

        consistency_result = {
            "status": "match",
            "batch": "1",
            "actual_count": 250,
            "declared_count": 250,
        }

        # 模拟时间
        with patch("time.strftime", return_value="2025-05-23 16:00:00"):
            # 调用函数
            display_summary_dashboard(
                cars, batch_results, consistency_result, "output.csv"
            )

        # 获取输出
        output = mock_console_output.getvalue()

        # 验证输出内容
        assert "车辆数据处理结果汇总" in output
        assert "共处理 250 条记录" in output
        assert "批次分布图表" in output
        assert "其他批次" in output  # 应该有"其他批次"类别
