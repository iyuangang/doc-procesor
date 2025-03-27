"""
安装脚本，主要配置在pyproject.toml中
"""

from setuptools import find_packages, setup

if __name__ == "__main__":
    setup(
        packages=find_packages(),
    )
