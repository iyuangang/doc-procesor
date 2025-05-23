"""
测试CLI命令结构和基本功能
"""

import os
from typing import Any, Dict, List, Optional

import pytest
from unittest import mock
from unittest.mock import patch, MagicMock, ANY

from src.cli.main import cli, process


# 基本验证测试，不使用Click的invoke方法
def test_cli_exists() -> None:
    """测试cli命令组是否存在"""
    assert callable(cli)
    assert callable(process)


@patch("src.cli.main.process_single_file")
def test_process_function_interface(mock_process_single_file: MagicMock) -> None:
    """测试process函数接口"""
    # 模拟返回值
    mock_process_single_file.return_value = [{"id": 1}]

    # 测试函数参数
    process_func = process.callback
    assert callable(process_func)

    # 检查process_single_file函数是否被导入
    from src.cli.main import process_single_file

    assert callable(process_single_file)


@patch("src.cli.main.setup_logging")
def test_logging_setup_import(mock_setup_logging: MagicMock) -> None:
    """测试日志设置函数是否被正确导入"""
    # 检查setup_logging函数是否被导入
    from src.cli.main import setup_logging

    assert callable(setup_logging)


@patch("src.cli.main.process_directory")
def test_process_directory_import(mock_process_directory: MagicMock) -> None:
    """测试目录处理函数是否被正确导入"""
    # 检查process_directory函数是否被导入
    from src.cli.main import process_directory

    assert callable(process_directory)


@patch("src.cli.main.load_config")
def test_load_config_import(mock_load_config: MagicMock) -> None:
    """测试配置加载函数是否被正确导入"""
    # 检查load_config函数是否被导入
    from src.cli.main import load_config

    assert callable(load_config)


def test_cli_command_structure() -> None:
    """测试CLI命令结构是否正确"""
    # 验证cli是一个命令组
    assert hasattr(cli, "commands")

    # 验证process是cli命令组的一个子命令
    assert "process" in cli.commands
    assert cli.commands["process"] == process


@patch("src.cli.main.click.echo")
@patch("src.cli.main.os.path.isdir")
def test_cli_process_params(mock_isdir: MagicMock, mock_echo: MagicMock) -> None:
    """测试cli命令参数定义"""
    # 检查process命令的参数
    assert process.params is not None

    # 找到参数名列表
    param_names = [p.name for p in process.params]

    # 验证需要的参数都在命令中定义了
    required_params = [
        "input_path",
        "output",
        "verbose",
        "pattern",
        "config",
        "log_config",
        "chunk_size",
        "skip_verification",
    ]
    for param in required_params:
        assert param in param_names
