"""
配置管理模块
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from doc_processor.exceptions import ConfigurationError


@dataclass
class ProcessorConfig:
    """处理器配置类"""

    # 基本配置
    verbose: bool = False
    preview: bool = False
    chunk_size: int = 1000
    cache_size_limit: int = 50 * 1024 * 1024  # 50MB
    cleanup_interval: int = 300  # 5分钟
    skip_count_check: bool = False

    # 搜索限制
    max_paragraphs_to_search: int = 30
    max_tables_to_search: int = 5

    # 性能配置
    max_processes: Optional[int] = None
    memory_limit: int = 1024 * 1024 * 1024  # 1GB

    # 扩展配置
    custom_settings: Dict[str, Any] = field(default_factory=dict)


def load_config(config_path: str = "config.yaml") -> ProcessorConfig:
    """
    从配置文件加载配置

    Args:
        config_path: 配置文件路径

    Returns:
        ProcessorConfig: 配置对象

    Raises:
        ConfigurationError: 配置加载失败
    """
    config = ProcessorConfig()

    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_config = yaml.safe_load(f)

            if not yaml_config:
                return config

            # 更新基本配置
            for key in [
                "verbose",
                "preview",
                "chunk_size",
                "cache_size_limit",
                "cleanup_interval",
                "skip_count_check",
                "max_paragraphs_to_search",
                "max_tables_to_search",
                "max_processes",
                "memory_limit",
            ]:
                if key in yaml_config:
                    setattr(config, key, yaml_config.pop(key))

            # 将剩余配置存储到custom_settings
            config.custom_settings = yaml_config
    except Exception as e:
        raise ConfigurationError(f"加载配置文件出错: {str(e)}", config_path)

    return config


def create_default_config(config_path: str = "config.yaml") -> None:
    """
    创建默认配置文件

    Args:
        config_path: 配置文件路径
    """
    default_config = {
        "verbose": False,
        "preview": False,
        "chunk_size": 1000,
        "cache_size_limit": 50 * 1024 * 1024,
        "cleanup_interval": 300,
        "skip_count_check": False,
        "max_paragraphs_to_search": 30,
        "max_tables_to_search": 5,
        "max_processes": None,
        "memory_limit": 1024 * 1024 * 1024,
        "logging": {
            "level": "INFO",
            "file": "logs/doc_processor.log",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    }

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        raise ConfigurationError(f"创建默认配置文件出错: {str(e)}", config_path)
