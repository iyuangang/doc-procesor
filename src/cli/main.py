"""
命令行入口模块 - 提供直接导入的命令行接口
"""

import click
import logging
import os
from typing import Optional, Dict, Any

from ..config.settings import load_config, setup_logging, ConfigurationError
from ..__main__ import process_directory, process_single_file


@click.group()
def cli():
    """车辆数据文档处理工具"""
    pass


@cli.command()
@click.argument(
    "input_path",
    type=click.Path(exists=True),
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=True),
    default="output",
    help="输出文件路径或目录",
)
@click.option("-v", "--verbose", is_flag=True, help="显示详细处理信息")
@click.option("--pattern", default="*.docx", help="文件匹配模式（用于目录输入）")
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False),
    help="配置文件路径",
)
@click.option(
    "--log-config",
    type=click.Path(exists=True, dir_okay=False),
    help="日志配置文件路径",
)
@click.option("--chunk-size", type=int, default=1000, help="数据处理块大小")
@click.option("--skip-verification", is_flag=True, help="跳过批次验证")
def process(
    input_path: str,
    output: str,
    verbose: bool,
    pattern: str,
    config: Optional[str] = None,
    log_config: Optional[str] = None,
    chunk_size: int = 1000,
    skip_verification: bool = False,
) -> None:
    """处理指定的docx文件或目录下的所有docx文件"""
    try:
        # 设置日志
        if log_config:
            setup_logging(log_config)
        else:
            setup_logging()

        logger = logging.getLogger(__name__)
        logger.info(f"开始处理任务: 输入={input_path}, 输出={output}")

        # 加载配置
        config_data = {}
        if config:
            try:
                config_data = load_config(config)
                logger.info(f"加载配置文件: {config}")
            except ConfigurationError as e:
                logger.error(f"加载配置失败: {str(e)}")
                click.echo(f"加载配置失败: {str(e)}")
                return

        # 设置配置参数
        if not config_data:
            config_data = {}
        if "performance" not in config_data:
            config_data["performance"] = {}
        config_data["performance"]["chunk_size"] = chunk_size

        if "document" not in config_data:
            config_data["document"] = {}
        config_data["document"]["skip_verification"] = skip_verification

        # 处理输入
        if os.path.isdir(input_path):
            # 处理目录
            result = process_directory(
                input_path, output, pattern, config_data, verbose
            )
            logger.info(f"目录处理结果: {result['status']}")
            logger.info(
                f"总文件数: {result['total_files']}, 成功: {result['success_files']}, "
                f"失败: {result['error_files']}, 总记录数: {result['total_records']}"
            )
            click.echo(
                f"处理完成 - 共处理 {result['total_files']} 个文件，"
                f"成功 {result['success_files']} 个，总记录数 {result['total_records']}"
            )
        else:
            # 处理单个文件
            cars = process_single_file(input_path, output, config_data, verbose)
            if cars:
                click.echo(f"处理成功 - 共提取 {len(cars)} 条记录")
            else:
                click.echo("处理失败 - 未能提取任何记录")

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"处理失败: {str(e)}", exc_info=True)
        click.echo(f"处理失败: {str(e)}")


if __name__ == "__main__":
    cli()
