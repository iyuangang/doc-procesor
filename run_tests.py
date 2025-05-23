#!/usr/bin/env python
"""
测试运行脚本 - 运行所有测试并生成覆盖率报告
"""

import os
import sys
import pytest


def main():
    """运行测试并返回退出代码"""
    # 添加项目根目录到 Python 路径
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # 运行测试
    return pytest.main(
        [
            "--cov=src",
            "--cov-report=term",
            "--cov-report=html",
            "--cov-report=xml",
            "tests",
        ]
    )


if __name__ == "__main__":
    sys.exit(main())
