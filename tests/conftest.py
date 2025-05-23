import os
import tempfile
from typing import Generator, Any

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    """提供Click命令测试运行器"""
    return CliRunner()


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    """提供临时目录"""
    with tempfile.TemporaryDirectory() as tmpdirname:
        old_dir = os.getcwd()
        os.chdir(tmpdirname)
        yield tmpdirname
        os.chdir(old_dir)


@pytest.fixture
def sample_docx(temp_dir: str) -> str:
    """创建一个示例docx文件"""
    filename = os.path.join(temp_dir, "test.docx")
    with open(filename, "wb") as f:
        f.write(b"test content")
    return filename


@pytest.fixture
def sample_config(temp_dir: str) -> str:
    """创建一个示例配置文件"""
    config_content = """
    {
        "document": {
            "skip_verification": false
        },
        "performance": {
            "chunk_size": 2000
        }
    }
    """
    config_file = os.path.join(temp_dir, "config.json")
    with open(config_file, "w") as f:
        f.write(config_content)
    return config_file


@pytest.fixture
def sample_log_config(temp_dir: str) -> str:
    """创建一个示例日志配置文件"""
    log_config_content = """
    {
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
                "stream": "ext://sys.stdout"
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"]
        }
    }
    """
    log_config_file = os.path.join(temp_dir, "logging.json")
    with open(log_config_file, "w") as f:
        f.write(log_config_content)
    return log_config_file
