"""
测试CLI入口点模块
"""

import os
import pytest


class TestCliMain:
    """测试CLI入口点模块"""

    def test_main_module_structure(self) -> None:
        """测试CLI入口点模块结构"""
        # 导入模块
        import src.cli.__main__

        # 验证模块包含正确的导入
        assert hasattr(src.cli.__main__, "cli")

        # 获取模块文件路径
        main_path = src.cli.__main__.__file__

        # 验证模块有正确的 __name__ 检查
        with open(main_path, "r", encoding="utf-8") as f:
            content = f.read()
            assert 'if __name__ == "__main__"' in content
            assert "cli()" in content
