#!/usr/bin/env python
"""
车辆数据文档处理器测试运行脚本

用于运行单元测试、集成测试和生成代码覆盖率报告
"""

import argparse
import os
import subprocess
import sys
from typing import List, Optional


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="运行车辆数据文档处理器测试")

    # 测试类型
    parser.add_argument(
        "-t",
        "--test-type",
        choices=["unit", "integration", "all"],
        default="all",
        help="指定要运行的测试类型: unit (单元测试), integration (集成测试), all (所有测试, 默认)",
    )

    # 测试模块
    parser.add_argument(
        "-m", "--module", help="指定要测试的模块，例如：processor, table, batch等"
    )

    # 测试标记
    parser.add_argument(
        "-k",
        "--markers",
        help="使用pytest标记表达式选择测试，例如：'smoke' 或 'not slow'",
    )

    # 详细输出
    parser.add_argument("-v", "--verbose", action="store_true", help="显示详细测试输出")

    # HTML报告
    parser.add_argument(
        "--html-report", action="store_true", help="生成HTML测试覆盖率报告"
    )

    # XML报告
    parser.add_argument(
        "--xml-report", action="store_true", help="生成XML测试覆盖率报告"
    )

    # 日志级别
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="设置日志级别",
    )

    # 失败时调试
    parser.add_argument("--pdb", action="store_true", help="在测试失败时启动调试器")

    # 指定测试文件或目录
    parser.add_argument(
        "test_path", nargs="?", help="要运行的测试文件或目录的路径(可选)"
    )

    return parser.parse_args()


def build_pytest_command(args: argparse.Namespace) -> List[str]:
    """
    构建pytest命令

    Args:
        args: 命令行参数

    Returns:
        pytest命令列表
    """
    cmd = ["pytest"]

    # 添加测试路径
    if args.test_path:
        cmd.append(args.test_path)
    elif args.test_type == "unit":
        cmd.append("tests/unit/")
    elif args.test_type == "integration":
        cmd.append("tests/integration/")

    # 如果指定了模块，添加模块路径
    if args.module:
        if args.test_path:
            # 如果已经指定了测试路径，不重复添加
            pass
        elif args.test_type == "all":
            cmd.append(f"tests/unit/{args.module}/ tests/integration/{args.module}/")
        else:
            cmd.append(f"tests/{args.test_type}/{args.module}/")

    # 添加详细模式
    if args.verbose:
        cmd.append("-v")

    # 添加标记表达式
    if args.markers:
        cmd.append(f"-m '{args.markers}'")

    # 添加测试覆盖率选项
    cmd.append("--cov=src")

    # 添加HTML报告
    if args.html_report:
        cmd.append("--cov-report=html")

    # 添加XML报告
    if args.xml_report:
        cmd.append("--cov-report=xml")

    # 默认添加终端报告
    cmd.append("--cov-report=term")

    # 添加日志级别
    cmd.append(f"--log-cli-level={args.log_level}")

    # 添加调试器选项
    if args.pdb:
        cmd.append("--pdb")

    return cmd


def run_tests(command: List[str]) -> int:
    """
    运行测试命令

    Args:
        command: 要运行的命令

    Returns:
        命令的退出码
    """
    # 打印要执行的命令
    cmd_str = " ".join(command)
    print(f"执行命令: {cmd_str}")

    # 执行命令
    result = subprocess.run(cmd_str, shell=True)
    return result.returncode


def main() -> int:
    """主入口点"""
    args = parse_args()

    # 构建并运行测试命令
    pytest_cmd = build_pytest_command(args)
    exit_code = run_tests(pytest_cmd)

    # 处理HTML报告信息
    if args.html_report and exit_code == 0:
        print("\n覆盖率报告已生成到 htmlcov/index.html")

    # 处理XML报告信息
    if args.xml_report and exit_code == 0:
        print("\n覆盖率XML报告已生成到 coverage.xml")

    # 返回测试的退出码
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
