"""
显示工具模块，用于格式化输出和命令行交互
"""

import textwrap
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

# 创建控制台对象
console = Console()


def print_title(title: str, style: str = "bold cyan") -> None:
    """
    打印标题

    Args:
        title: 标题文本
        style: 样式
    """
    console.print(f"\n[{style}]{title}[/{style}]")


def print_info(message: str, style: str = "blue") -> None:
    """
    打印信息

    Args:
        message: 信息文本
        style: 样式
    """
    console.print(f"[{style}]{message}[/{style}]")


def print_success(message: str) -> None:
    """
    打印成功信息

    Args:
        message: 信息文本
    """
    console.print(f"[bold green]✅ {message}[/bold green]")


def print_warning(message: str) -> None:
    """
    打印警告信息

    Args:
        message: 警告文本
    """
    console.print(f"[bold yellow]⚠️ {message}[/bold yellow]")


def print_error(message: str) -> None:
    """
    打印错误信息

    Args:
        message: 错误文本
    """
    console.print(f"[bold red]❌ {message}[/bold red]")


def create_progress_bar() -> Progress:
    """
    创建进度条

    Returns:
        Progress: 进度条对象
    """
    return Progress(
        "[progress.description]{task.description}",
        SpinnerColumn(),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        "[bold blue]{task.completed}/{task.total}",
        "•",
        TimeRemainingColumn(),
        "•",
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )


def display_table(
    title: str,
    headers: List[str],
    rows: List[List[str]],
    title_style: str = "bold cyan",
    header_style: str = "bold green",
    border_style: str = "blue",
) -> None:
    """
    显示表格数据

    Args:
        title: 表格标题
        headers: 表头列表
        rows: 行数据列表
        title_style: 标题样式
        header_style: 表头样式
        border_style: 边框样式
    """
    # 创建表格
    table = Table(
        title=title,
        title_style=title_style,
        show_header=True,
        header_style=header_style,
        border_style=border_style,
    )

    # 添加列
    for header in headers:
        table.add_column(header)

    # 添加行
    for row in rows:
        table.add_row(*row)

    # 显示表格
    console.print()
    console.print(table)
    console.print()


def display_statistics(
    total_count: int,
    energy_saving_count: int,
    new_energy_count: int,
    output_file: str,
) -> None:
    """
    显示处理统计信息

    Args:
        total_count: 总记录数
        energy_saving_count: 节能型车辆数
        new_energy_count: 新能源车辆数
        output_file: 输出文件
    """
    # 在显示表格前添加标题，表明这是关键信息
    console.print()
    console.print("[bold cyan]📊 关键信息：处理统计报告[/bold cyan]")

    # 创建统计表格
    stats_table = Table(
        title="📊 处理统计报告",
        title_style="bold cyan",
        show_header=True,
        header_style="bold green",
        border_style="blue",
    )

    # 添加列
    stats_table.add_column("项目", style="cyan")
    stats_table.add_column("数值", justify="right", style="green")
    stats_table.add_column("占比", justify="right", style="yellow")

    # 计算百分比
    energy_saving_percent = (
        energy_saving_count / total_count * 100 if total_count > 0 else 0
    )
    new_energy_percent = new_energy_count / total_count * 100 if total_count > 0 else 0

    # 添加行
    stats_table.add_row("📝 总记录数", f"{total_count:,}", "100%")
    stats_table.add_row(
        "🚗 节能型汽车", f"{energy_saving_count:,}", f"{energy_saving_percent:.1f}%"
    )
    stats_table.add_row(
        "⚡ 新能源汽车", f"{new_energy_count:,}", f"{new_energy_percent:.1f}%"
    )
    stats_table.add_row("💾 输出文件", output_file, "")

    # 显示表格
    console.print(stats_table)
    console.print()


def display_comparison(new_models: Set[str], removed_models: Set[str]) -> None:
    """
    显示型号对比结果

    Args:
        new_models: 新增型号集合
        removed_models: 移除型号集合
    """
    # 创建对比表格
    compare_table = Table(
        title="🔄 型号对比",
        title_style="bold cyan",
        show_header=True,
        header_style="bold green",
        border_style="blue",
    )

    # 添加列
    compare_table.add_column("变更类型", style="cyan")
    compare_table.add_column("数量", justify="right", style="green")
    compare_table.add_column("型号列表", style="yellow")

    # 添加新增型号
    if new_models:
        models_text = "\n".join(f"✨ {model}" for model in sorted(new_models))
        compare_table.add_row("➕ 新增", str(len(new_models)), models_text)

    # 添加移除型号
    if removed_models:
        models_text = "\n".join(f"❌ {model}" for model in sorted(removed_models))
        compare_table.add_row("➖ 移除", str(len(removed_models)), models_text)

    if new_models or removed_models:
        console.print()
        console.print(compare_table)
        console.print()
    else:
        console.print(Panel("[green]✅ 没有型号变更[/green]", border_style="green"))


def display_batch_verification(batch_results: Dict[str, Dict[str, Any]]) -> None:
    """
    显示批次验证结果

    Args:
        batch_results: 批次验证结果
    """
    if not batch_results:
        console.print(
            Panel(
                "[yellow]⚠️ 没有批次数据可供验证[/yellow]",
                title="批次验证",
                border_style="yellow",
            )
        )
        return

    # 创建批次汇总表格
    summary_table = Table(
        title="🔍 批次数据汇总",
        title_style="bold cyan",
        show_header=True,
        header_style="bold green",
        border_style="blue",
    )

    # 添加列
    summary_table.add_column("批次", style="cyan")
    summary_table.add_column("记录数", justify="right", style="green")
    summary_table.add_column("表格数", justify="right", style="yellow")

    # 计算批次总数，如果超过一定数量，只显示部分
    batch_count = len(batch_results)
    show_all = batch_count <= 50  # 只有50个批次以内才全部显示

    # 添加批次数据
    total_records = 0
    total_tables = 0

    sorted_batches = sorted(batch_results.items())

    # 如果批次太多，只显示前20个和后20个
    if not show_all:
        display_batches = sorted_batches[:20] + sorted_batches[-20:]
        console.print(
            f"[yellow]注意：只显示前20个和后20个批次（共{batch_count}个批次）[/yellow]"
        )
    else:
        display_batches = sorted_batches

    for batch, data in display_batches:
        total_records += data["total"]
        table_count = len(data["table_counts"])
        total_tables += table_count
        summary_table.add_row(f"第{batch}批", str(data["total"]), str(table_count))

    # 如果有省略的批次，添加省略提示行
    if not show_all and batch_count > 40:
        summary_table.add_row(f"... (省略 {batch_count - 40} 个批次) ...", "...", "...")

    # 添加合计行
    summary_table.add_row(
        "[bold]合计[/bold]",
        f"[bold]{total_records}[/bold]",
        f"[bold]{total_tables}[/bold]",
    )

    # 在表格前添加标题，表明这是关键信息
    console.print()
    console.print("[bold cyan]📊 关键信息：批次数据汇总[/bold cyan]")
    console.print(summary_table)
    console.print()


def print_doc_tree(tree: Tree) -> None:
    """
    打印文档树形结构

    Args:
        tree: 树形结构对象
    """
    console.print("\n")
    console.print(Panel(tree, border_style="blue"))
    console.print()
