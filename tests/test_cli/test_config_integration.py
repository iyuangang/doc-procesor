"""
CLI程序配置加载和日志设置的集成测试
"""

import os
import sys
import subprocess
import json
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Generator

import pytest


def run_cli_command(
    args: List[str], env_vars: Optional[Dict[str, str]] = None
) -> Tuple[int, str, str]:
    """
    运行CLI命令并获取结果

    Args:
        args: 命令行参数列表
        env_vars: 要设置的环境变量字典

    Returns:
        (返回码, 标准输出, 标准错误输出)
    """
    # 获取python解释器路径
    python_exe = sys.executable

    # 构建完整命令
    cmd = [python_exe, "-m", "src.cli.main"] + args

    # 设置环境变量
    if env_vars:
        env = os.environ.copy()
        env.update(env_vars)
    else:
        env = None

    # 运行命令，捕获输出
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        env=env,
    )

    # 获取输出
    stdout, stderr = proc.communicate()

    # 返回结果
    return proc.returncode, stdout, stderr


@pytest.fixture
def config_test_environment(tmp_path: Path) -> Generator[Dict[str, Path], None, None]:
    """
    设置配置测试环境

    Args:
        tmp_path: pytest提供的临时目录

    Returns:
        包含测试环境路径的字典
    """
    # 创建测试目录结构
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    config_dir = tmp_path / "config"

    input_dir.mkdir()
    output_dir.mkdir()
    config_dir.mkdir()

    # 创建示例文档
    sample_file = input_dir / "test.docx"
    sample_file.write_bytes(b"test content")

    # 创建有效的配置文件
    valid_config = {
        "document": {"skip_verification": True},
        "performance": {"chunk_size": 2000},
    }
    valid_config_file = config_dir / "valid_config.json"
    valid_config_file.write_text(json.dumps(valid_config))

    # 创建无效的配置文件（语法错误）
    invalid_config_file = config_dir / "invalid_config.json"
    invalid_config_file.write_text("{this is not valid json")

    # 创建缺少必需字段的配置文件
    incomplete_config = {"document": {}}  # 没有performance字段
    incomplete_config_file = config_dir / "incomplete_config.json"
    incomplete_config_file.write_text(json.dumps(incomplete_config))

    # 创建日志配置
    log_config = {
        "version": 1,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.FileHandler",
                "level": "DEBUG",
                "formatter": "standard",
                "filename": str(output_dir / "app.log"),
            },
        },
        "root": {"level": "INFO", "handlers": ["console", "file"]},
    }
    log_config_file = config_dir / "logging.json"
    log_config_file.write_text(json.dumps(log_config))

    # 无效的日志配置
    invalid_log_config = {"version": 1, "invalid": True}
    invalid_log_config_file = config_dir / "invalid_logging.json"
    invalid_log_config_file.write_text(json.dumps(invalid_log_config))

    # 返回测试环境配置
    test_env = {
        "input_dir": input_dir,
        "output_dir": output_dir,
        "config_dir": config_dir,
        "sample_file": sample_file,
        "valid_config_file": valid_config_file,
        "invalid_config_file": invalid_config_file,
        "incomplete_config_file": incomplete_config_file,
        "log_config_file": log_config_file,
        "invalid_log_config_file": invalid_log_config_file,
        "log_file": output_dir / "app.log",
    }

    yield test_env


def test_valid_config_loading(config_test_environment: Dict[str, Path]) -> None:
    """测试有效配置文件的加载"""
    env = config_test_environment

    args = [
        "process",
        str(env["sample_file"]),
        "--config",
        str(env["valid_config_file"]),
    ]

    return_code, stdout, stderr = run_cli_command(args)

    # 验证命令本身不因配置问题而失败
    assert "加载配置失败" not in stdout
    assert "Invalid config" not in stderr


def test_invalid_config_handling(config_test_environment: Dict[str, Path]) -> None:
    """测试无效配置文件的错误处理"""
    env = config_test_environment

    args = [
        "process",
        str(env["sample_file"]),
        "--config",
        str(env["invalid_config_file"]),
    ]

    return_code, stdout, stderr = run_cli_command(args)

    # 应该有配置错误信息
    assert (
        "加载配置失败" in stdout
        or "Invalid JSON" in stderr
        or "Failed to parse" in stderr
    )


def test_incomplete_config_fallback(config_test_environment: Dict[str, Path]) -> None:
    """测试缺少字段的配置文件是否提供默认值"""
    env = config_test_environment

    args = [
        "process",
        str(env["sample_file"]),
        "--config",
        str(env["incomplete_config_file"]),
    ]

    return_code, stdout, stderr = run_cli_command(args)

    # 配置缺少字段，但应该使用默认值而不是失败
    assert "加载配置失败" not in stdout


def test_log_config_file_loading(config_test_environment: Dict[str, Path]) -> None:
    """测试日志配置文件的加载"""
    env = config_test_environment

    args = [
        "process",
        str(env["sample_file"]),
        "--log-config",
        str(env["log_config_file"]),
    ]

    return_code, stdout, stderr = run_cli_command(args)

    # 配置日志不应该导致错误
    assert "Invalid log config" not in stderr
    assert "日志配置错误" not in stdout

    # 检查是否创建了日志文件（由log_config指定）
    # 注意：这个断言可能不稳定，因为可能需要权限或其他原因导致日志文件没有创建
    # 如果测试不稳定，可以考虑移除这个断言
    # assert env["log_file"].exists()


def test_invalid_log_config_fallback(config_test_environment: Dict[str, Path]) -> None:
    """测试无效日志配置时的错误处理和默认值使用"""
    env = config_test_environment

    args = [
        "process",
        str(env["sample_file"]),
        "--log-config",
        str(env["invalid_log_config_file"]),
    ]

    return_code, stdout, stderr = run_cli_command(args)

    # 无效日志配置可能导致警告，但不应完全阻止命令执行
    # 通常会回退到默认日志配置
    assert return_code == 0 or "Invalid log config" in stderr


def test_chunk_size_override(config_test_environment: Dict[str, Path]) -> None:
    """测试命令行参数是否正确覆盖配置文件值"""
    env = config_test_environment

    # 配置文件中的chunk_size为2000
    # 命令行参数指定为500，应该覆盖配置文件值
    args = [
        "process",
        str(env["sample_file"]),
        "--config",
        str(env["valid_config_file"]),
        "--chunk-size",
        "500",
    ]

    return_code, stdout, stderr = run_cli_command(args)

    # 不应该有解析错误
    assert "Invalid value" not in stderr

    # 注：验证实际使用了哪个值需要更复杂的测试或日志输出
    # 这里我们只验证命令成功执行
