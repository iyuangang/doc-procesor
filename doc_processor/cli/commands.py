"""
命令行界面模块
"""

import os
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.tree import Tree

from doc_processor.config import ProcessorConfig, load_config
from doc_processor.core import DataExporter, DocProcessor
from doc_processor.utils import (
    TimingContext,
    display_comparison,
    display_statistics,
    print_doc_tree,
    print_error,
    print_info,
    print_title,
)

# 创建控制台对象
console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli() -> None:
    """车辆数据文档处理工具."""
    pass


@cli.command()
@click.argument("input_path", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="输出CSV文件路径")
@click.option("-c", "--config", type=click.Path(), help="配置文件路径")
@click.option("-v", "--verbose", is_flag=True, help="显示详细信息")
@click.option("--preview", is_flag=True, help="预览文档结构")
@click.option("--compare", type=click.Path(), help="对比的旧数据文件")
@click.option("--recursive", is_flag=True, help="递归处理子目录中的文件")
@click.option("--skip-count-check", is_flag=True, help="跳过记录数验证")
def process(
    input_path: str,
    output: Optional[str],
    config: Optional[str],
    verbose: bool,
    preview: bool,
    compare: Optional[str],
    recursive: bool,
    skip_count_check: bool,
) -> None:
    """处理文档文件或目录."""
    try:
        # 准备输出文件路径
        if not output and not preview:
            base = os.path.basename(input_path)
            if os.path.isdir(input_path):
                output = f"{base}_output.csv"
            else:
                output = f"{os.path.splitext(base)[0]}.csv"
            print_info(f"未指定输出路径，将使用默认路径: {output}")

        # 加载配置
        processor_config = load_config(config) if config else ProcessorConfig()
        processor_config.verbose = verbose
        processor_config.preview = preview
        processor_config.skip_count_check = skip_count_check

        # 创建处理器
        processor = DocProcessor(processor_config)

        # 使用计时上下文
        with TimingContext("总处理时间", verbose=verbose):
            if preview:
                # 预览模式
                if os.path.isdir(input_path):
                    print_error("预览模式不支持目录处理")
                    return

                # 预览文档结构
                print_title("📄 文档结构预览")
                structure = processor.preview_document(input_path)

                # 创建树形结构
                doc_tree = Tree("📑 文档结构")

                # 添加节点
                for section in structure.root.children:
                    section_node = doc_tree.add(
                        f"[bold blue]{section.title}[/bold blue]"
                    )
                    for subsection in section.children:
                        subsec_node = section_node.add(
                            f"[cyan]{subsection.title}[/cyan]"
                        )
                        for child in subsection.children:
                            if child.node_type == "table":
                                subsec_node.add(
                                    f"[green]📊 表格: {child.title}[/green]"
                                )
                            else:
                                subsec_node.add(f"[yellow]{child.title}[/yellow]")

                # 显示树形结构
                print_doc_tree(doc_tree)

            else:
                # 处理模式
                if os.path.isdir(input_path):
                    # 处理目录
                    results = processor.process_directory(input_path, recursive)

                    # 没有结果
                    if not results:
                        print_error("未能从目录提取任何有效数据")
                        return

                    # 合并结果
                    exporter = DataExporter()
                    collections = list(results.values())
                    merged_collection = exporter.merge_collections(collections)

                    # 导出合并后的数据
                    exporter.export_to_csv(merged_collection, output)

                    # 显示统计信息
                    counts = merged_collection.count_by_type()
                    display_statistics(
                        len(merged_collection),
                        counts.get(2, 0),  # 节能型
                        counts.get(1, 0),  # 新能源
                        output,
                    )

                    # 如果需要对比
                    if compare:
                        added, removed = exporter.compare_model_changes(
                            merged_collection, compare
                        )
                        display_comparison(added, removed)

                else:
                    # 处理单个文件
                    car_collection = processor.process_file(input_path)

                    # 导出数据
                    exporter = DataExporter()
                    exporter.export_to_csv(car_collection, output)

                    # 显示统计信息
                    counts = car_collection.count_by_type()
                    display_statistics(
                        len(car_collection),
                        counts.get(2, 0),  # 节能型
                        counts.get(1, 0),  # 新能源
                        output,
                    )

                    # 如果需要对比
                    if compare:
                        added, removed = exporter.compare_model_changes(
                            car_collection, compare
                        )
                        display_comparison(added, removed)

    except Exception as e:
        print_error(f"处理失败: {str(e)}")
        raise


@cli.command()
@click.option("--config", type=click.Path(), help="配置文件保存路径")
@click.option("--logging", type=click.Path(), help="日志配置保存路径")
def init(config: Optional[str], logging: Optional[str]) -> None:
    """初始化默认配置文件."""
    from doc_processor.config.settings import create_default_config
    from doc_processor.utils.logging_utils import create_default_logging_config

    try:
        if config:
            create_default_config(config)
            print_info(f"默认配置文件已创建: {config}")

        if logging:
            create_default_logging_config(logging)
            print_info(f"默认日志配置文件已创建: {logging}")

        if not config and not logging:
            create_default_config("config.yaml")
            create_default_logging_config("logging.yaml")
            print_info("默认配置文件已创建: config.yaml, logging.yaml")

    except Exception as e:
        print_error(f"初始化配置失败: {str(e)}")


if __name__ == "__main__":
    cli()
