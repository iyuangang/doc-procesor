# -*- coding: utf-8 -*-
"""
pytest配置文件
"""

import os
import sys
import pytest
import tempfile
from typing import Generator, Any

import click.testing

# 将项目根目录添加到导入路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.fixture(scope="session")
def test_data_dir():
    """返回测试数据目录路径"""
    return os.path.join(project_root, "tests", "data")


@pytest.fixture(scope="session")
def sample_docx_path():
    """返回样本docx文件路径"""
    data_dir = os.path.join(project_root, "tests", "data")
    return os.path.join(data_dir, "sample.docx")


@pytest.fixture(scope="session")
def sample_car_dict():
    """返回样本车辆信息字典"""
    return {
        "vmodel": "测试型号",
        "企业名称": "测试企业",
        "品牌": "测试品牌",
        "批次": "1",
        "energytype": 1,
        "category": "新能源",
        "sub_type": "轿车",
    }


@pytest.fixture(scope="session")
def sample_car_list():
    """返回样本车辆信息列表"""
    return [
        {
            "vmodel": "型号A",
            "企业名称": "企业X",
            "品牌": "品牌M",
            "批次": "1",
            "energytype": 1,
            "category": "新能源",
            "sub_type": "轿车",
        },
        {
            "vmodel": "型号B",
            "企业名称": "企业Y",
            "品牌": "品牌N",
            "批次": "1",
            "energytype": 2,
            "category": "节能型",
            "sub_type": "SUV",
        },
        {
            "vmodel": "型号C",
            "企业名称": "企业Z",
            "品牌": "品牌O",
            "批次": "2",
            "energytype": 1,
            "category": "新能源",
            "sub_type": "轿车",
        },
    ]


@pytest.fixture(scope="function")
def temp_dir(tmpdir):
    """创建临时目录"""
    return tmpdir.strpath


@pytest.fixture(scope="function")
def mock_empty_config():
    """返回空配置"""
    return {}


@pytest.fixture
def runner() -> click.testing.CliRunner:
    """提供Click命令测试运行器"""
    return click.testing.CliRunner()


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
