"""
CLI程序的集成测试 - 实际调用应用程序
"""

import os
import sys
import subprocess
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Tuple, Generator, Optional

import pytest


def run_cli_command(args: List[str]) -> Tuple[int, str, str]:
    """
    运行CLI命令并获取结果

    Args:
        args: 命令行参数列表

    Returns:
        (返回码, 标准输出, 标准错误输出)
    """
    # 获取python解释器路径
    python_exe = sys.executable

    # 构建完整命令
    cmd = [python_exe, "-m", "src.cli.main"] + args

    # 运行命令，捕获输出
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )

    # 获取输出
    stdout, stderr = proc.communicate()

    # 返回结果
    return proc.returncode, stdout, stderr


def test_help_command() -> None:
    """测试帮助命令是否正常工作"""
    return_code, stdout, stderr = run_cli_command(["--help"])

    # 验证命令成功执行
    assert return_code == 0

    # 验证输出包含预期内容
    assert "车辆数据文档处理工具" in stdout
    assert "process" in stdout  # 应该列出子命令

    # 忽略导入警告，只检查是否有真正的错误
    # 警告内容: "found in sys.modules after import of package..."
    assert "Error:" not in stderr


def test_process_help_command() -> None:
    """测试process子命令的帮助是否显示正确"""
    return_code, stdout, stderr = run_cli_command(["process", "--help"])

    # 验证命令成功执行
    assert return_code == 0

    # 验证输出包含预期内容
    assert "处理指定的docx文件或目录下的所有docx文件" in stdout
    assert "--output" in stdout
    assert "--verbose" in stdout
    assert "--pattern" in stdout

    # 忽略导入警告
    assert "Error:" not in stderr


def test_missing_arguments() -> None:
    """测试缺少必要参数时的错误处理"""
    return_code, stdout, stderr = run_cli_command(["process"])

    # 验证命令因参数错误而失败
    assert return_code != 0

    # 验证输出包含错误信息
    assert "Missing argument" in stderr
    assert "INPUT_PATH" in stderr


def test_nonexistent_input() -> None:
    """测试输入不存在时的错误处理"""
    nonexistent_file = "nonexistent_file.docx"

    return_code, stdout, stderr = run_cli_command(["process", nonexistent_file])

    # 验证命令因路径不存在而失败
    assert return_code != 0

    # 验证输出包含错误信息
    assert "Path" in stderr and "does not exist" in stderr


@pytest.mark.parametrize(
    "option,value",
    [
        ("--output", "custom_output"),
        ("--pattern", "*.txt"),
        ("--chunk-size", "500"),
        ("--skip-verification", None),
    ],
)
def test_option_parsing(option: str, value: Optional[str], tmp_path: Any) -> None:
    """测试各个选项是否被正确解析

    Args:
        option: 要测试的选项名
        value: 选项值，None表示是布尔标志
        tmp_path: pytest提供的临时目录
    """
    # 创建示例文档
    test_file = tmp_path / "test.docx"
    test_file.write_bytes(b"test content")

    # 构建命令
    args = ["process", str(test_file)]
    if value is None:
        args.append(option)
    else:
        args.extend([option, value])

    # 运行命令
    return_code, stdout, stderr = run_cli_command(args)

    # 命令可能会失败，因为我们没有提供真实的文档处理逻辑
    # 但它应该通过参数解析
    assert "Invalid value" not in stderr
    assert "Error: No such option" not in stderr


def test_process_with_config(tmp_path: Any) -> None:
    """测试使用配置文件"""
    # 创建示例文档
    test_file = tmp_path / "test.docx"
    test_file.write_bytes(b"test content")

    # 创建配置文件
    config_data = {
        "document": {"skip_verification": True},
        "performance": {"chunk_size": 2000},
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config_data))

    # 运行命令
    args = ["process", str(test_file), "--config", str(config_file)]
    return_code, stdout, stderr = run_cli_command(args)

    # 验证输出
    assert "Invalid value" not in stderr
    assert "Error: No such option" not in stderr
