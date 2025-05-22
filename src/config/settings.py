"""
配置管理模块 - 处理应用程序配置
"""

import os
import logging
import logging.config
from datetime import datetime
from typing import Dict, Any, Union

import yaml


class ConfigurationError(Exception):
    """配置错误异常"""

    pass


def load_config(config_path: str = "config/config.yaml") -> Dict[Any, Any]:
    """
    加载配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        包含配置的字典

    Raises:
        ConfigurationError: 加载配置出错
    """
    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config: Dict[Any, Any] = yaml.safe_load(f)
            return config
        return {}
    except Exception as e:
        raise ConfigurationError(f"加载配置文件出错: {str(e)}")


def setup_logging(
    default_path: str = "config/logging.yaml",
    default_level: Union[str, int] = logging.INFO,
    env_key: str = "LOG_CFG",
) -> None:
    """
    配置日志记录

    Args:
        default_path: 日志配置文件路径
        default_level: 默认日志级别
        env_key: 环境变量键名
    """
    path = os.getenv(env_key, default_path)
    if os.path.exists(path):
        with open(path, "rt", encoding="utf-8") as f:
            try:
                config = yaml.safe_load(f.read())
                _ensure_log_directory(config)
                logging.config.dictConfig(config)
                logging.info("使用配置文件配置日志: %s", path)
            except Exception as e:
                print(f"加载日志配置出错: {e}")
                setup_default_logging(default_level)
    else:
        setup_default_logging(default_level)


def _ensure_log_directory(config: Dict[str, Any]) -> None:
    """
    确保日志目录存在

    Args:
        config: 日志配置字典
    """
    handlers = config.get("handlers", {})
    log_files = []

    # 收集所有日志文件路径
    for handler in handlers.values():
        if "filename" in handler:
            log_files.append(handler["filename"])

    # 确保目录存在
    for log_file in log_files:
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)


def setup_default_logging(level: Any) -> None:
    """
    设置默认日志配置

    Args:
        level: 日志级别
    """
    log_dir = "logs"
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

    logging.info("使用默认配置设置日志")


class Settings:
    """
    应用程序设置类，用于管理全局配置
    """

    def __init__(self, config_path: str = "config/config.yaml") -> None:
        """
        初始化设置

        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = load_config(config_path)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键，可以使用点号分隔，如 'performance.chunk_size'
            default: 默认值

        Returns:
            配置值
        """
        if "." in key:
            keys = key.split(".")
            value = self.config
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value
        else:
            return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        设置配置项

        Args:
            key: 配置键，可以使用点号分隔，如 'performance.chunk_size'
            value: 配置值
        """
        if "." in key:
            keys = key.split(".")
            config = self.config
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            config[keys[-1]] = value
        else:
            self.config[key] = value

    def save(self) -> None:
        """
        保存配置到文件

        Raises:
            ConfigurationError: 保存配置出错
        """
        try:
            config_dir = os.path.dirname(self.config_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)

            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
        except Exception as e:
            raise ConfigurationError(f"保存配置文件出错: {str(e)}")


# 创建全局设置实例
settings = Settings()
