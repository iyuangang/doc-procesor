"""
包的入口点，用于支持 'python -m src.cli' 命令
"""

from .main import main

# 当使用 'python -m src.cli' 运行时，会执行这个文件
if __name__ == "__main__":
    main()
