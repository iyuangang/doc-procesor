"""
配置模块
"""

from doc_processor.config.settings import (
    ProcessorConfig,
    create_default_config,
    load_config,
)

__all__ = ["ProcessorConfig", "load_config", "create_default_config"]
