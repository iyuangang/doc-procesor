#!/usr/bin/env python3
"""
车辆数据文档处理器 - 安装脚本
"""

import os
from setuptools import setup, find_packages

# 读取requirements.txt中的依赖
with open("requirements.txt") as f:
    requirements = f.read().splitlines()

# 读取README.md作为长描述
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="doc-processor",
    version="1.0.0",
    description="车辆数据文档处理工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="iyuangang",
    author_email="yuangang@me.com",
    url="https://github.com/iyuangang/doc-processor",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "doc-processor=doc_processor:main",
        ],
    },
    py_modules=["doc_processor"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Utilities",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="document processing, vehicle data, docx parser",
)
