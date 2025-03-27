"""
日志工具模块
"""

import logging
import logging.config
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml

from doc_processor.exceptions import ConfigurationError


def setup_logging(
    default_path: str = "logging.yaml",
    default_level: int = logging.INFO,
    env_key: str = "LOG_CFG",
    log_dir: str = "logs",
) -> None:
    """
    配置日志记录

    Args:
        default_path: 默认配置文件路径
        default_level: 默认日志级别
        env_key: 环境变量键
        log_dir: 日志目录
    """
    path = os.getenv(env_key, default_path)
    if os.path.exists(path):
        with open(path, "rt", encoding="utf-8") as f:
            try:
                config = yaml.safe_load(f.read())
                logging.config.dictConfig(config)
            except Exception as e:
                print(f"加载日志配置出错: {e}")
                setup_default_logging(default_level, log_dir)
    else:
        setup_default_logging(default_level, log_dir)


def setup_default_logging(level: int, log_dir: str = "logs") -> None:
    """
    设置默认日志配置

    Args:
        level: 日志级别
        log_dir: 日志目录
    """
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"doc_processor_{timestamp}.log")

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def create_logger(
    name: str, level: Union[int, str] = logging.INFO, log_file: Optional[str] = None
) -> logging.Logger:
    """
    创建自定义日志记录器

    Args:
        name: 记录器名称
        level: 日志级别
        log_file: 日志文件路径

    Returns:
        日志记录器
    """
    logger = logging.getLogger(name)

    # 如果已经配置过级别和处理器，直接返回
    if logger.level != 0 and logger.handlers:
        return logger

    logger.setLevel(level)

    # 创建格式化器
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # 添加控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 如果指定了日志文件，添加文件处理器
    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # 添加文件处理器
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def create_default_logging_config(config_path: str = "logging.yaml") -> None:
    """
    创建默认日志配置文件

    Args:
        config_path: 配置文件路径
    """
    config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            },
            "simple": {"format": "%(levelname)s - %(message)s"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "standard",
                "filename": "logs/doc_processor.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf8",
            },
        },
        "loggers": {
            "": {  # root logger
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": True,
            },
            "doc_processor": {
                "handlers": ["console", "file"],
                "level": "DEBUG",
                "propagate": False,
            },
        },
    }

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
    except Exception as e:
        raise ConfigurationError(f"创建默认日志配置文件出错: {str(e)}", config_path)
