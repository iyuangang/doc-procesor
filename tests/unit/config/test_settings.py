"""
测试配置设置模块
"""

import os
import tempfile
import logging
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

import pytest
import yaml

from src.config.settings import (
    load_config,
    setup_logging,
    setup_default_logging,
    _ensure_log_directory,
    Settings,
    ConfigurationError,
)


class TestLoadConfig:
    """测试配置加载函数"""

    def test_load_config_success(self) -> None:
        """测试成功加载配置文件"""
        # 创建临时配置文件
        config_data = {"test": {"key": "value"}, "number": 42}
        config_yaml = yaml.dump(config_data)

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            temp_file.write(config_yaml.encode("utf-8"))
            temp_path = temp_file.name

        try:
            # 加载配置
            result = load_config(temp_path)

            # 验证结果
            assert result == config_data
            assert result["test"]["key"] == "value"
            assert result["number"] == 42
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_load_config_nonexistent_file(self) -> None:
        """测试加载不存在的配置文件"""
        # 使用一个不太可能存在的路径
        result = load_config("/path/to/nonexistent/config.yaml")
        assert result == {}

    def test_load_config_error(self) -> None:
        """测试加载错误的配置文件"""
        # 创建格式错误的YAML文件
        invalid_yaml = "invalid: yaml: content: - ["

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            temp_file.write(invalid_yaml.encode("utf-8"))
            temp_path = temp_file.name

        try:
            # 尝试加载，应该抛出异常
            with pytest.raises(ConfigurationError):
                load_config(temp_path)
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestSetupLogging:
    """测试日志设置函数"""

    @patch("logging.config.dictConfig")
    @patch("logging.info")
    def test_setup_logging_with_config(
        self, mock_info: MagicMock, mock_dict_config: MagicMock
    ) -> None:
        """测试使用配置文件设置日志"""
        # 创建临时日志配置文件
        log_config = {
            "version": 1,
            "formatters": {"standard": {"format": "%(message)s"}},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "level": "INFO",
                    "formatter": "standard",
                }
            },
            "root": {"level": "INFO", "handlers": ["console"]},
        }
        log_yaml = yaml.dump(log_config)

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            temp_file.write(log_yaml.encode("utf-8"))
            temp_path = temp_file.name

        try:
            # 设置日志
            with patch("os.path.exists", return_value=True):
                setup_logging(temp_path)

            # 验证调用
            mock_dict_config.assert_called_once()
            mock_info.assert_called_once()
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    @patch("src.config.settings.setup_default_logging")
    def test_setup_logging_nonexistent_file(
        self, mock_default_logging: MagicMock
    ) -> None:
        """测试使用不存在的配置文件设置日志"""
        # 使用一个不太可能存在的路径
        with patch("os.path.exists", return_value=False):
            setup_logging("/path/to/nonexistent/logging.yaml")

        # 验证调用了默认日志设置
        mock_default_logging.assert_called_once()

    @patch("src.config.settings.setup_default_logging")
    def test_setup_logging_with_error(self, mock_default_logging: MagicMock) -> None:
        """测试日志配置出错时的处理"""
        # 模拟加载配置文件出错
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="invalid: yaml: - [")):
                setup_logging("invalid_logging.yaml")

        # 验证调用了默认日志设置
        mock_default_logging.assert_called_once()


class TestEnsureLogDirectory:
    """测试确保日志目录存在的函数"""

    @patch("os.path.exists")
    @patch("os.makedirs")
    def test_ensure_log_directory(
        self, mock_makedirs: MagicMock, mock_exists: MagicMock
    ) -> None:
        """测试确保日志目录存在"""
        # 设置模拟
        mock_exists.return_value = False

        # 创建测试配置
        config = {
            "handlers": {
                "file1": {"filename": "logs/app.log"},
                "file2": {"filename": "logs/error.log"},
                "console": {"class": "logging.StreamHandler"},  # 没有文件名
            }
        }

        # 调用函数
        _ensure_log_directory(config)

        # 验证结果
        assert mock_makedirs.call_count == 2
        mock_makedirs.assert_any_call("logs")

    def test_ensure_log_directory_no_handlers(self) -> None:
        """测试没有处理程序的情况"""
        # 创建测试配置
        config = {"no_handlers": {}}

        # 调用函数，不应该抛出异常
        _ensure_log_directory(config)


class TestSetupDefaultLogging:
    """测试设置默认日志的函数"""

    @patch("os.path.exists")
    @patch("os.makedirs")
    @patch("logging.basicConfig")
    @patch("logging.info")
    def test_setup_default_logging(
        self,
        mock_info: MagicMock,
        mock_basic_config: MagicMock,
        mock_makedirs: MagicMock,
        mock_exists: MagicMock,
    ) -> None:
        """测试设置默认日志"""
        # 设置模拟
        mock_exists.return_value = False

        # 调用函数
        setup_default_logging(logging.INFO)

        # 验证结果
        mock_makedirs.assert_called_once_with("logs")
        mock_basic_config.assert_called_once()
        mock_info.assert_called_once_with("使用默认配置设置日志")


class TestSettings:
    """测试设置类"""

    def test_settings_init(self) -> None:
        """测试初始化设置类"""
        # 创建临时配置文件
        config_data = {"test": {"key": "value"}, "number": 42}
        config_yaml = yaml.dump(config_data)

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as temp_file:
            temp_file.write(config_yaml.encode("utf-8"))
            temp_path = temp_file.name

        try:
            # 创建设置实例
            settings = Settings(temp_path)

            # 验证结果
            assert settings.config_path == temp_path
            assert settings.config == config_data
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_settings_get(self) -> None:
        """测试获取配置项"""
        # 创建设置实例，使用内存中的配置
        settings = Settings()
        settings.config = {
            "test": {"key": "value", "nested": {"deep": "data"}},
            "number": 42,
        }

        # 测试获取顶级配置项
        assert settings.get("number") == 42
        assert settings.get("nonexistent") is None
        assert settings.get("nonexistent", "default") == "default"

        # 测试获取嵌套配置项
        assert settings.get("test.key") == "value"
        assert settings.get("test.nested.deep") == "data"
        assert settings.get("test.nonexistent") is None
        assert settings.get("test.nonexistent", "default") == "default"
        assert settings.get("nonexistent.key") is None

    def test_settings_set(self) -> None:
        """测试设置配置项"""
        # 创建设置实例
        settings = Settings()
        settings.config = {"test": {"key": "value"}}

        # 测试设置顶级配置项
        settings.set("number", 42)
        assert settings.config["number"] == 42

        # 测试设置嵌套配置项
        settings.set("test.key", "new_value")
        assert settings.config["test"]["key"] == "new_value"

        # 测试设置不存在的嵌套配置项
        settings.set("new.nested.key", "value")
        assert settings.config["new"]["nested"]["key"] == "value"

    def test_settings_save(self) -> None:
        """测试保存配置"""
        # 创建临时目录
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建配置文件路径
            config_path = os.path.join(temp_dir, "config", "test_config.yaml")

            # 创建设置实例
            settings = Settings(config_path)
            settings.config = {"test": {"key": "value"}, "number": 42}

            # 保存配置
            settings.save()

            # 验证文件是否创建
            assert os.path.exists(config_path)

            # 验证文件内容
            with open(config_path, "r", encoding="utf-8") as f:
                loaded_config = yaml.safe_load(f)
                assert loaded_config == settings.config

    def test_settings_save_error(self) -> None:
        """测试保存配置出错"""
        # 创建设置实例，使用不可写的路径
        settings = Settings("/root/nonwritable/config.yaml")
        settings.config = {"test": "value"}

        # 尝试保存，应该抛出异常
        with patch("builtins.open", side_effect=PermissionError("权限不足")):
            with pytest.raises(ConfigurationError):
                settings.save()
