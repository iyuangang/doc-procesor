"""
测试主程序入口模块
"""

import os
import sys
import tempfile
import argparse
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest

from src.__main__ import (
    parse_args,
    process_single_file,
    process_directory,
    main,
)
from src.models.car_info import BatchInfo


class TestParseArgs:
    """测试命令行参数解析函数"""

    @patch("argparse.ArgumentParser.parse_args")
    def test_parse_args_defaults(self, mock_parse_args: MagicMock) -> None:
        """测试默认参数解析"""
        # 设置模拟返回值
        mock_args = argparse.Namespace(
            input="input_path",
            output="output",
            config="config.yaml",
            log_config="logging.yaml",
            verbose=False,
            chunk_size=1000,
            skip_verification=False,
            pattern="*.docx",
            classic_display=False,
            dashboard_theme="default",
        )
        mock_parse_args.return_value = mock_args

        # 调用函数
        args = parse_args()

        # 验证结果
        assert args.input == "input_path"
        assert args.output == "output"
        assert args.config == "config.yaml"
        assert args.log_config == "logging.yaml"
        assert args.verbose is False
        assert args.chunk_size == 1000
        assert args.skip_verification is False
        assert args.pattern == "*.docx"
        assert args.classic_display is False
        assert args.dashboard_theme == "default"


class TestProcessSingleFile:
    """测试单文件处理函数"""

    @patch("src.__main__.DocProcessor")
    def test_process_single_file_success(self, mock_doc_processor: MagicMock) -> None:
        """测试成功处理单个文件"""
        # 设置模拟
        mock_processor = MagicMock()
        mock_processor.process.return_value = [
            {"vmodel": "车型1", "energytype": 1, "batch": "1"}
        ]
        mock_doc_processor.return_value = mock_processor

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            test_file = os.path.join(temp_dir, "test.docx")
            with open(test_file, "w") as f:
                f.write("test content")

            # 调用函数
            result = process_single_file(
                test_file, temp_dir, {"test": "config"}, verbose=True
            )

            # 验证结果
            assert len(result) == 1
            assert result[0]["vmodel"] == "车型1"
            assert result[0]["energytype"] == 1
            assert result[0]["batch"] == "1"

            # 验证调用
            mock_doc_processor.assert_called_once_with(
                test_file, verbose=True, config={"test": "config"}
            )
            mock_processor.process.assert_called_once()
            mock_processor.save_to_csv.assert_called_once()

    def test_process_single_file_nonexistent(self) -> None:
        """测试处理不存在的文件"""
        # 使用一个不太可能存在的文件路径
        file_path = "/path/to/nonexistent/file.docx"

        # 调用函数
        result = process_single_file(file_path, "output", {})

        # 验证结果
        assert result == []

    @patch("src.__main__.DocProcessor")
    def test_process_single_file_exception(self, mock_doc_processor: MagicMock) -> None:
        """测试处理文件时发生异常"""
        # 设置模拟以抛出异常
        mock_processor = MagicMock()
        mock_processor.process.side_effect = Exception("测试异常")
        mock_doc_processor.return_value = mock_processor

        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建测试文件
            test_file = os.path.join(temp_dir, "test.docx")
            with open(test_file, "w") as f:
                f.write("test content")

            # 调用函数
            result = process_single_file(test_file, temp_dir, {})

            # 验证结果
            assert result == []


class TestProcessDirectory:
    """测试目录处理函数"""

    @patch("src.__main__.process_single_file")
    @patch("glob.glob")
    def test_process_directory_success(
        self, mock_glob: MagicMock, mock_process_single_file: MagicMock
    ) -> None:
        """测试成功处理目录"""
        # 设置模拟
        mock_glob.return_value = ["file1.docx", "file2.docx"]
        mock_process_single_file.side_effect = [
            [{"vmodel": "车型1", "energytype": 1, "batch": "1"}],
            [{"vmodel": "车型2", "energytype": 2, "batch": "2"}],
        ]

        # 调用函数
        result = process_directory("input_dir", "output_dir", "*.docx", {}, True)

        # 验证结果
        assert result["status"] == "success"
        assert result["total_files"] == 2
        assert result["processed_files"] == 2
        assert result["success_files"] == 2
        assert result["error_files"] == 0
        assert result["total_records"] == 2

        # 验证调用
        assert mock_process_single_file.call_count == 2

    @patch("glob.glob")
    def test_process_directory_no_files(self, mock_glob: MagicMock) -> None:
        """测试处理没有文件的目录"""
        # 设置模拟
        mock_glob.return_value = []

        # 调用函数
        result = process_directory("input_dir", "output_dir")

        # 验证结果
        assert result["status"] == "error"
        assert result["total_files"] == 0
        assert result["message"] == "未找到匹配的文件: input_dir\\*.docx"

    @patch("src.__main__.process_single_file")
    @patch("glob.glob")
    def test_process_directory_with_errors(
        self, mock_glob: MagicMock, mock_process_single_file: MagicMock
    ) -> None:
        """测试处理目录时有文件处理错误"""
        # 设置模拟
        mock_glob.return_value = ["file1.docx", "file2.docx", "file3.docx"]
        mock_process_single_file.side_effect = [
            [],  # 第一个文件处理失败
            [{"vmodel": "车型2", "energytype": 2, "batch": "2"}],  # 第二个文件成功
            Exception("测试异常"),  # 第三个文件抛出异常
        ]

        # 调用函数
        result = process_directory("input_dir", "output_dir", "*.docx", {}, False)

        # 验证结果
        assert result["status"] == "success"
        assert result["total_files"] == 3
        assert result["processed_files"] == 2  # 只有两个文件被处理（第三个抛出异常）
        assert result["success_files"] == 1  # 只有一个文件成功
        assert (
            result["error_files"] == 2
        )  # 两个文件失败（第一个返回空，第三个抛出异常）

    @patch("src.__main__.pd.DataFrame.to_csv")
    @patch("src.__main__.verify_batch_consistency")
    @patch("src.__main__.verify_all_batches")
    @patch("src.__main__.process_single_file")
    @patch("glob.glob")
    def test_process_directory_with_dashboard(
        self,
        mock_glob: MagicMock,
        mock_process_single_file: MagicMock,
        mock_verify_all_batches: MagicMock,
        mock_verify_batch_consistency: MagicMock,
        mock_to_csv: MagicMock,
    ) -> None:
        """测试处理目录并显示仪表盘"""
        # 设置模拟
        mock_glob.return_value = ["file1.docx", "file2.docx"]
        mock_process_single_file.side_effect = [
            [{"vmodel": "车型1", "energytype": 1, "batch": "1"}],
            [{"vmodel": "车型2", "energytype": 2, "batch": "2"}],
        ]
        mock_verify_all_batches.return_value = {
            "1": {"total": 1, "table_counts": {"1": 1}},
            "2": {"total": 1, "table_counts": {"2": 1}},
        }
        mock_verify_batch_consistency.return_value = {
            "status": "match",
            "batch": "1",
            "actual_count": 2,
            "declared_count": 2,
        }

        # 调用函数
        with patch("src.__main__.display_summary_dashboard") as mock_display:
            result = process_directory(
                "input_dir",
                "output_dir",
                "*.docx",
                {"output": {"use_dashboard": True}},
                True,
            )

            # 验证结果
            assert result["status"] == "success"
            assert result["total_files"] == 2
            assert result["total_records"] == 2

            # 验证调用
            mock_display.assert_called_once()
            mock_to_csv.assert_called_once()


class TestMain:
    """测试主函数"""

    @patch("src.__main__.parse_args")
    @patch("src.__main__.setup_logging")
    @patch("src.__main__.load_config")
    @patch("src.__main__.process_single_file")
    @patch("os.path.isdir")
    @patch("os.makedirs")
    def test_main_single_file(
        self,
        mock_makedirs: MagicMock,
        mock_isdir: MagicMock,
        mock_process_single_file: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
        mock_parse_args: MagicMock,
    ) -> None:
        """测试处理单个文件的主函数流程"""
        # 设置模拟
        mock_args = MagicMock()
        mock_args.input = "test.docx"
        mock_args.output = "output"
        mock_args.config = "config.yaml"
        mock_args.log_config = "logging.yaml"
        mock_args.verbose = False
        mock_args.chunk_size = 1000
        mock_args.skip_verification = False
        mock_args.pattern = "*.docx"
        mock_args.classic_display = False
        mock_args.dashboard_theme = "default"
        mock_parse_args.return_value = mock_args

        mock_isdir.return_value = False  # 不是目录，是单个文件
        mock_process_single_file.return_value = [
            {"vmodel": "车型1", "energytype": 1, "batch": "1"}
        ]
        mock_load_config.return_value = {}

        # 模拟配置文件存在
        with patch("os.path.exists", return_value=True):
            # 调用函数
            result = main()

            # 验证结果
            assert result == 0
            mock_process_single_file.assert_called_once()

    @patch("src.__main__.parse_args")
    @patch("src.__main__.setup_logging")
    @patch("src.__main__.load_config")
    @patch("src.__main__.process_directory")
    @patch("os.path.isdir")
    def test_main_directory(
        self,
        mock_isdir: MagicMock,
        mock_process_directory: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
        mock_parse_args: MagicMock,
    ) -> None:
        """测试处理目录的主函数流程"""
        # 设置模拟
        mock_args = MagicMock()
        mock_args.input = "input_dir"
        mock_args.output = "output"
        mock_args.config = "config.yaml"
        mock_args.log_config = "logging.yaml"
        mock_args.verbose = True
        mock_args.chunk_size = 1000
        mock_args.skip_verification = False
        mock_args.pattern = "*.docx"
        mock_args.classic_display = False
        mock_args.dashboard_theme = "default"
        mock_parse_args.return_value = mock_args

        mock_isdir.return_value = True  # 是目录
        mock_process_directory.return_value = {
            "status": "success",
            "total_files": 2,
            "processed_files": 2,
            "success_files": 2,
            "error_files": 0,
            "total_records": 2,
        }
        mock_load_config.return_value = {}

        # 模拟配置文件存在
        with patch("os.path.exists", return_value=True):
            # 调用函数
            result = main()

            # 验证结果
            assert result == 0
            mock_process_directory.assert_called_once()

    @patch("src.__main__.parse_args")
    @patch("src.__main__.setup_logging")
    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_main_config_not_found(
        self,
        mock_makedirs: MagicMock,
        mock_exists: MagicMock,
        mock_setup_logging: MagicMock,
        mock_parse_args: MagicMock,
    ) -> None:
        """测试配置文件不存在的情况"""
        # 设置模拟
        mock_args = MagicMock()
        mock_args.input = "test.docx"
        mock_args.output = "output"
        mock_args.config = "nonexistent_config.yaml"
        mock_args.log_config = "logging.yaml"
        mock_args.verbose = False
        mock_args.chunk_size = 1000
        mock_args.skip_verification = False
        mock_args.pattern = "*.docx"
        mock_args.classic_display = False
        mock_args.dashboard_theme = "default"
        mock_parse_args.return_value = mock_args

        mock_exists.return_value = False  # 配置文件不存在

        # 模拟process_single_file
        with patch("src.__main__.process_single_file", return_value=[]) as mock_process:
            with patch("os.path.isdir", return_value=False):
                # 调用函数
                result = main()

                # 验证结果
                assert result == 0
                # 验证使用了默认配置
                config_arg = mock_process.call_args[0][2]
                assert "performance" in config_arg
                assert "document" in config_arg
                assert "output" in config_arg

    @patch("src.__main__.parse_args")
    @patch("src.__main__.setup_logging")
    @patch("src.__main__.load_config")
    @patch("os.makedirs")
    def test_main_config_error(
        self,
        mock_makedirs: MagicMock,
        mock_load_config: MagicMock,
        mock_setup_logging: MagicMock,
        mock_parse_args: MagicMock,
    ) -> None:
        """测试加载配置文件出错的情况"""
        # 设置模拟
        mock_args = MagicMock()
        mock_args.input = "test.docx"
        mock_args.output = "output"
        mock_args.config = "config.yaml"
        mock_args.log_config = "logging.yaml"
        mock_args.verbose = False
        mock_args.chunk_size = 1000
        mock_args.skip_verification = False
        mock_args.pattern = "*.docx"
        mock_args.classic_display = False
        mock_args.dashboard_theme = "default"
        mock_parse_args.return_value = mock_args

        mock_load_config.side_effect = Exception("配置文件格式错误")

        # 模拟配置文件存在
        with patch("os.path.exists", return_value=True):
            # 模拟process_single_file
            with patch(
                "src.__main__.process_single_file", return_value=[]
            ) as mock_process:
                with patch("os.path.isdir", return_value=False):
                    # 调用函数
                    result = main()

                    # 验证结果
                    assert result == 0
                    # 验证使用了默认配置
                    config_arg = mock_process.call_args[0][2]
                    assert "performance" in config_arg
                    assert "document" in config_arg
                    assert "output" in config_arg
