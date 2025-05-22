"""
控制台输出模块 - 提供控制台显示和格式化功能
"""

import textwrap
from typing import Dict, Any, List, Set, Optional, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)
from rich.text import Text
from rich.tree import Tree

from ..models.document_node import DocumentNode, DocumentStructure

# 创建控制台对象
console = Console()


def display_statistics(
    total_count: int, energy_saving_count: int, new_energy_count: int, output_file: str
) -> None:
    """
    显示处理统计信息

    Args:
        total_count: 总记录数
        energy_saving_count: 节能型汽车数量
        new_energy_count: 新能源汽车数量
        output_file: 输出文件路径
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


def display_doc_content(doc_structure: DocumentStructure) -> None:
    """
    使用树形结构显示文档内容

    Args:
        doc_structure: 文档结构对象
    """

    def get_node_style(node: DocumentNode) -> Tuple[str, str]:
        """获取节点的样式和图标"""
        styles = {
            "root": ("bold blue", "📑"),
            "section": ("bold cyan", "📌"),
            "subsection": ("bold yellow", "📎"),
            "numbered_section": ("bold green", "🔢"),
            "numbered_subsection": ("bold magenta", "📍"),
            "table": ("bold blue", "📊"),
            "text": ("white", "📝"),
            "note": ("bold magenta", "ℹ️"),
            "correction": ("bold red", "⚠️"),
        }
        return styles.get(node.node_type, ("white", "•"))

    def add_node_to_tree(tree: Tree, node: DocumentNode) -> None:
        """递归添加节点到树中"""
        style, icon = get_node_style(node)

        # 构建节点标题
        title = f"{icon} {node.title}"
        if node.batch_number and node.level <= 1:
            title += f" [dim](第{node.batch_number}批)[/dim]"

        # 创建节点
        branch = tree.add(f"[{style}]{title}[/{style}]")

        # 添加内容（如果有且与标题不同）
        if node.content and node.content != node.title:
            content_lines = textwrap.wrap(node.content, width=100)
            for line in content_lines:
                branch.add(f"[dim]{line}[/dim]")

        # 添加元数据（如果有）
        if node.metadata:
            meta_branch = branch.add("[dim]元数据[/dim]")
            for key, value in node.metadata.items():
                meta_branch.add(f"[dim]{key}: {value}[/dim]")

        # 递归处理子节点
        for child in node.children:
            add_node_to_tree(branch, child)

    # 创建主树
    tree = Tree("📄 文档结构", style="bold blue")
    for child in doc_structure.root.children:
        add_node_to_tree(tree, child)

    # 显示树
    console.print("\n")
    console.print(Panel(tree, border_style="blue"))
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


def display_batch_verification(batch_results: Dict[str, Any]) -> None:
    """
    显示批次验证结果

    Args:
        batch_results: 批次验证结果字典
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


def display_consistency_result(result: Dict[str, Any]) -> None:
    """
    显示批次一致性验证结果

    Args:
        result: 一致性验证结果字典
    """
    # 在显示结果前添加标题，表明这是关键信息
    console.print()
    console.print("[bold cyan]📊 关键信息：数据一致性检查[/bold cyan]")

    if result["status"] == "no_batch":
        console.print(
            Panel(
                "[yellow]⚠️ 未找到批次号，无法验证数据一致性[/yellow]",
                title="数据一致性检查",
                border_style="yellow",
            )
        )
        return

    if result["status"] == "unknown":
        console.print(
            Panel(
                f"[yellow]⚠️ 第{result['batch']}批：未找到总记录数声明，实际记录数为 {result['actual_count']}[/yellow]",
                title="数据一致性检查",
                border_style="yellow",
            )
        )
    elif result["status"] == "match":
        console.print(
            Panel(
                f"[green]✅ 第{result['batch']}批：记录数匹配，共 {result['actual_count']} 条记录[/green]",
                title="数据一致性检查",
                border_style="green",
            )
        )
    elif result["status"] == "mismatch":
        diff_text = f"差异 {result['difference']} 条" if "difference" in result else ""
        console.print(
            Panel(
                f"[red]❌ 第{result['batch']}批：记录数不匹配！声明 {result['declared_count']}, 实际 {result['actual_count']}, {diff_text}[/red]",
                title="⚠️ 数据一致性检查",
                border_style="red",
            )
        )
    elif result["status"] == "internal_match":
        console.print(
            Panel(
                f"[green]✅ 第{result['batch']}批：内部一致性检查通过，表格记录总数 {result['actual_count']} 与处理结果数 {result['processed_count']} 一致[/green]",
                title="数据一致性检查",
                border_style="green",
            )
        )
    elif result["status"] == "internal_mismatch":
        diff_text = f"差异 {result['difference']} 条" if "difference" in result else ""
        console.print(
            Panel(
                f"[red]❌ 第{result['batch']}批：内部一致性检查失败！表格记录总数 {result['actual_count']} 与处理结果数 {result['processed_count']} 不一致，{diff_text}[/red]",
                title="⚠️ 数据一致性检查",
                border_style="red",
            )
        )

    # 显示表格记录分布
    table_counts = result.get("table_counts", {})
    if table_counts:
        count_table = Table(
            title="📊 表格记录分布",
            title_style="bold cyan",
            show_header=True,
            header_style="bold green",
            border_style="blue",
        )
        count_table.add_column("表格ID", style="cyan")
        count_table.add_column("记录数", justify="right", style="green")
        count_table.add_column("占比", justify="right", style="yellow")

        total = result.get("actual_count", sum(table_counts.values()))

        for table_id, count in sorted(table_counts.items()):
            percentage = (count / total * 100) if total > 0 else 0
            count_table.add_row(
                f"表格 {table_id}" if not isinstance(table_id, str) else table_id,
                str(count),
                f"{percentage:.1f}%",
            )

        console.print(count_table)


def create_progress_bar(total: int) -> Progress:
    """
    创建进度条并返回进度条对象

    Args:
        total: 任务总数

    Returns:
        Progress对象，已添加任务
    """
    progress = Progress(
        "[progress.description]{task.description}",
        SpinnerColumn(),
        BarColumn(bar_width=None),
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

    progress.add_task("[bold cyan]🔄 处理文件", total=total)

    return progress


def print_docx_content(doc_path: str) -> None:
    """
    打印文档内容预览，显示所有元素的详细信息

    Args:
        doc_path: 文档路径
    """
    try:
        from docx import Document
        from docx.document import Document as DocxDocument

        doc: DocxDocument = Document(doc_path)
        console.print(
            Panel(
                f"[bold cyan]文件详细内容: {doc_path}[/bold cyan]", border_style="cyan"
            )
        )

        # 创建一个树形结构
        tree = Tree(f"📄 {doc_path}", style="bold blue")

        # 添加段落内容
        paragraphs_node = tree.add("[bold magenta]📝 段落内容[/bold magenta]")
        for i, para in enumerate(doc.paragraphs, 1):
            text = para.text.strip()
            if text:
                style_name = para.style.name if para.style else "默认样式"
                para_node = paragraphs_node.add(
                    f"[blue]段落 {i}[/blue] ([yellow]{style_name}[/yellow])"
                )
                if "批" in text:
                    para_node.add(f"🔖 [bold red]{text}[/bold red]")
                elif "节能型汽车" in text or "新能源汽车" in text:
                    para_node.add(f"📌 [bold green]{text}[/bold green]")
                elif text.startswith("（") and not any(str.isdigit() for str in text):
                    para_node.add(f"📎 [bold yellow]{text}[/bold yellow]")
                elif any(
                    marker in text
                    for marker in ["勘误", "关于", "符合", "技术要求", "自动转入"]
                ):
                    para_node.add(f"ℹ️ [bold magenta]{text}[/bold magenta]")
                else:
                    para_node.add(Text(textwrap.shorten(text, width=100)))

        # 添加表格内容
        tables_node = tree.add("[bold cyan]📊 表格内容[/bold cyan]")
        for i, table in enumerate(doc.tables, 1):
            if table.rows:
                table_node = tables_node.add(
                    f"[blue]表格 {i}[/blue] ({len(table.rows)}行 x {len(table.rows[0].cells)}列)"
                )

                # 创建表格预览
                preview_table = Table(
                    show_header=True,
                    header_style="bold green",
                    border_style="blue",
                    title=f"表格 {i} 预览",
                    title_style="bold cyan",
                )

                # 添加表头
                headers = [cell.text.strip() for cell in table.rows[0].cells]
                for header in headers:
                    preview_table.add_column(header, overflow="fold")

                # 添加数据行预览
                for row_idx, row in enumerate(table.rows[1:6], 1):  # 只显示前5行数据
                    cells = [cell.text.strip() for cell in row.cells]
                    if any(cells):  # 跳过空行
                        preview_table.add_row(*cells)

                table_node.add(preview_table)

        console.print(tree)

    except Exception as e:
        console.print(
            Panel(
                f"[bold red]预览文件 {doc_path} 时出错: {e}[/bold red]",
                border_style="red",
            )
        )
