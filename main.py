from pathlib import Path
import pandas as pd  # type: ignore
from docx import Document  # type: ignore
from docx.document import Document as DocxDocument
from docx.table import Table as DocxTable
import re
from typing import Dict, Any, Optional, List, Union, Set
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
    TimeElapsedColumn,
)
from rich.syntax import Syntax
from rich.text import Text
from rich.tree import Tree
import textwrap
from functools import lru_cache
import cProfile
import pstats
from io import StringIO
import time
import psutil
import os
from lxml import etree
import gc


# 创建控制台对象
console = Console()


# 预编译正则表达式
BATCH_NUMBER_PATTERN = re.compile(r"第([一二三四五六七八九十百零\d]+)批")
WHITESPACE_PATTERN = re.compile(r"\s+")
CHINESE_NUMBER_PATTERN = re.compile(r"([一二三四五六七八九十百零]+)")

# 中文数字映射表
CN_NUMS = {
    "零": "0",
    "一": "1",
    "二": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
    "十": "10",
    "百": "100",
}


@lru_cache(maxsize=1024)
def cn_to_arabic(cn_num: str) -> str:
    """
    将中文数字转换为阿拉伯数字，使用缓存提高性能
    """
    if cn_num.isdigit():
        return cn_num

    # 处理个位数
    if len(cn_num) == 1:
        return CN_NUMS.get(cn_num, cn_num)

    # 处理"百"开头的数字
    if "百" in cn_num:
        parts = cn_num.split("百")
        hundreds = int(CN_NUMS[parts[0]])
        if not parts[1]:  # 整百
            return str(hundreds * 100)
        # 处理带"零"的情况
        if parts[1].startswith("零"):
            ones = int(CN_NUMS[parts[1][-1]])
            return str(hundreds * 100 + ones)
        return str(hundreds * 100 + int(cn_to_arabic(parts[1])))

    # 处理"十"开头的数字
    if cn_num.startswith("十"):
        if len(cn_num) == 1:
            return "10"
        return "1" + CN_NUMS[cn_num[1]]

    # 处理带十的两位数
    if "十" in cn_num:
        parts = cn_num.split("十")
        tens = CN_NUMS[parts[0]]
        if len(parts) == 1 or not parts[1]:
            return f"{tens}0"
        ones = CN_NUMS[parts[1]]
        return f"{tens}{ones}"

    return CN_NUMS.get(cn_num, cn_num)


@lru_cache(maxsize=1024)
def extract_batch_number(text: str) -> Optional[str]:
    """
    从文本中提取批次号，使用缓存提高性能
    """
    # 先尝试匹配完整的批次号格式
    match = BATCH_NUMBER_PATTERN.search(text)
    if match:
        num = match.group(1)
        # 如果是纯数字，直接返回
        if num.isdigit():
            return num

        # 转换中文数字
        try:
            return cn_to_arabic(num)
        except (KeyError, ValueError):
            return None

    # 如果没有找到批次号格式，尝试直接转换纯中文数字
    if any(char in text for char in "一二三四五六七八九十百零"):
        try:
            # 提取连续的中文数字
            match = CHINESE_NUMBER_PATTERN.search(text)
            if match:
                return cn_to_arabic(match.group(1))
        except (KeyError, ValueError):
            pass

    return None


@lru_cache(maxsize=1024)
def clean_text(text: str) -> str:
    """
    清理文本内容，使用缓存提高性能
    """
    # 移除多余的空白字符
    text = WHITESPACE_PATTERN.sub(" ", text.strip())
    # 统一全角字符到半角
    text = text.replace("，", ",").replace("；", ";")
    return text


def validate_car_info(car_info: dict[str, Any]) -> tuple[bool, str]:
    """
    验证车辆信息的完整性和正确性

    Returns:
        (是否有效, 错误信息)
    """
    required_fields = ["企业名称", "型号"]
    for field in required_fields:
        if field not in car_info or not car_info[field]:
            return False, f"缺少必要字段: {field}"

    if "car_type" not in car_info:
        return False, "缺少车型标识"

    if car_info["car_type"] not in [1, 2]:
        return False, f"无效的车型标识: {car_info['car_type']}"

    return True, ""


def get_table_type(
    headers: List[str], current_category: Optional[str], current_type: Optional[str]
) -> tuple[str, str]:
    """
    根据表头判断表格类型
    """
    header_set: Set[str] = set(headers)

    # 如果没有当前分类或类型，使用默认值
    current_category = current_category or "未知"
    current_type = current_type or "未知"

    # 定义各类型的特征字段
    type_features: Dict[tuple[str, str], Dict[str, Any]] = {
        ("节能型", "（一）乘用车"): {
            "required": {"排量(ml)", "综合燃料消耗量"},
            "optional": {"DCT", "档位数"},
        },
        ("节能型", "（二）轻型商用车"): {
            "required": {"燃料种类"},
            "condition": lambda h: "CNG" in str(h),
        },
        ("节能型", "（三）重型商用车"): {
            "required": {"燃料种类"},
            "condition": lambda h: "LNG" in str(h),
        },
        ("新能源", "（一）插电式混合动力乘用车"): {
            "required": {"纯电动续驶里程", "燃料消耗量", "通用名称"}
        },
        ("新能源", "（二）纯电动商用车"): {
            "required": {"纯电动续驶里程", "动力蓄电池总能量"}
        },
        ("新能源", "（三）插电式混合动力商用车"): {
            "required": {"纯电动续驶里程", "燃料消耗量"},
            "exclude": {"通用名称"},
        },
        ("新能源", "（四）燃料电池商用车"): {"required": {"燃料电池系统额定功率"}},
    }

    # 检查每种类型的特征
    for (category, type_name), features in type_features.items():
        required = features.get("required", set())
        optional = features.get("optional", set())
        condition = features.get("condition", lambda _: True)
        exclude = features.get("exclude", set())

        if (
            required & header_set == required  # 必需字段都存在
            and not (exclude & header_set)  # 排除字段不存在
            and condition(headers)  # 满足额外条件
        ):
            return category, type_name

    return current_category, current_type


def process_car_info(
    car_info: dict[str, Any], batch_number: Optional[str] = None
) -> dict[str, Any]:
    """
    处理车辆信息，合并和标准化字段

    Args:
        car_info: 原始车辆信息字典
        batch_number: 批次号

    Returns:
        处理后的车辆信息字典
    """
    # 添加批次号
    if batch_number:
        car_info["batch"] = batch_number

    # 合并型号字段
    model_fields = ["产品型号", "车辆型号"]
    model_values = []
    for field in model_fields:
        if field in car_info:
            value = car_info.pop(field)
            if value:
                model_values.append(clean_text(value))

    if model_values:
        car_info["型号"] = model_values[0]  # 使用第一个非空的型号

    # 标准化字段名称
    field_mapping = {
        "通用名称": "品牌",
        "商标": "品牌",
    }

    for old_field, new_field in field_mapping.items():
        if old_field in car_info:
            value = car_info.pop(old_field)
            if value and new_field not in car_info:
                car_info[new_field] = clean_text(value)

    # 清理其他字段的文本
    for key in car_info:
        if isinstance(car_info[key], str):
            car_info[key] = clean_text(car_info[key])

    return car_info


def extract_doc_content(doc_path: str) -> tuple[list[str], list[dict[str, str]]]:
    """
    提取文档中除表格外的内容，并分离额外信息
    """
    doc: DocxDocument = Document(doc_path)
    paragraphs: list[str] = []
    extra_info: list[dict[str, str]] = []
    current_section: Optional[str] = None
    batch_found = False
    batch_number = None

    # 额外信息的标识词和对应类型
    info_types: dict[str, str] = {
        "勘误": "勘误",
        "关于": "政策",
        "符合": "说明",
        "技术要求": "说明",
        "自动转入": "说明",
        "第二部分": "说明",
    }

    # 用于收集连续的额外信息文本
    current_extra_info: Optional[dict[str, str]] = None

    def save_current_extra_info() -> None:
        """保存当前的额外信息"""
        nonlocal current_extra_info
        if current_extra_info:
            # 清理和规范化内容
            content = current_extra_info["content"]
            # 移除多余的空白字符
            content = re.sub(r"\s+", " ", content)
            # 移除换行符
            content = content.replace("\n", " ")
            current_extra_info["content"] = content.strip()

            # 添加批次号
            if batch_number:
                current_extra_info["batch"] = batch_number

            # 检查是否需要合并相同类型和章节的信息
            for info in extra_info:
                if (
                    info["type"] == current_extra_info["type"]
                    and info["section"] == current_extra_info["section"]
                ):
                    info["content"] = (
                        info["content"] + " " + current_extra_info["content"]
                    )
                    current_extra_info = None
                    return

            extra_info.append(current_extra_info)
            current_extra_info = None

    # 遍历文档段落
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            # 如果遇到空行，保存当前的额外信息
            if current_extra_info:
                save_current_extra_info()
            continue

        # 检查批次号
        if not batch_found and "批" in text:
            extracted_batch = extract_batch_number(text)
            if extracted_batch:
                batch_number = extracted_batch
                paragraphs.append(text)  # 将批次号信息放在最前面
                batch_found = True
                continue

        # 识别主要分类
        if text.startswith("一、") or text.startswith("二、"):
            save_current_extra_info()
            current_section = text
            paragraphs.append(text)
        # 识别子分类
        elif text.startswith("（"):
            save_current_extra_info()
            current_section = text
            paragraphs.append(text)
        # 识别额外信息
        elif any(marker in text for marker in info_types.keys()):
            # 如果当前文本包含新的标识词，保存之前的信息并创建新的
            if current_extra_info:
                save_current_extra_info()

            # 创建新的额外信息
            info_type = next((t for m, t in info_types.items() if m in text), "其他")
            current_extra_info = {
                "section": current_section or "文档说明",
                "type": info_type,
                "content": text,
            }
        # 如果当前有未处理的额外信息，将文本追加到内容中
        elif current_extra_info is not None:
            current_extra_info["content"] = current_extra_info["content"] + " " + text
        else:
            paragraphs.append(text)

    # 保存最后一条未处理的额外信息
    save_current_extra_info()

    return paragraphs, extra_info


def print_docx_content(doc_path: str) -> None:
    """
    打印文档内容预览，显示所有元素的详细信息
    """
    try:
        doc: DocxDocument = Document(doc_path)
        console.print(f"\n[bold cyan]文件详细内容: {doc_path}[/bold cyan]")

        # 创建一个树形结构
        tree = Tree(f"📄 {Path(doc_path).name}")

        # 添加段落内容
        paragraphs_node = tree.add("[bold]📝 段落内容[/bold]")
        for i, para in enumerate(doc.paragraphs, 1):
            text = para.text.strip()
            if text:
                # 显示段落编号、样式和内容
                style_name = para.style.name if para.style else "默认样式"
                para_node = paragraphs_node.add(
                    f"[blue]段落 {i}[/blue] ([yellow]{style_name}[/yellow])"
                )
                # 处理段落内容，检测特殊标记
                if "批" in text:
                    para_node.add(f"[bold red]批次信息: {text}[/bold red]")
                elif text.startswith(("一、", "二、")):
                    para_node.add(f"[bold green]主分类: {text}[/bold green]")
                elif text.startswith("（"):
                    para_node.add(f"[bold yellow]子分类: {text}[/bold yellow]")
                elif any(
                    marker in text
                    for marker in ["勘误", "关于", "符合", "技术要求", "自动转入"]
                ):
                    para_node.add(f"[bold magenta]额外信息: {text}[/bold magenta]")
                else:
                    para_node.add(Text(textwrap.shorten(text, width=100)))

        # 添加表格内容
        tables_node = tree.add("[bold]📊 表格内容[/bold]")
        for i, table in enumerate(doc.tables, 1):
            if table.rows:
                table_node = tables_node.add(
                    f"[blue]表格 {i}[/blue] ({len(table.rows)}行 x {len(table.rows[0].cells)}列)"
                )

                # 显示表头
                headers = [cell.text.strip() for cell in table.rows[0].cells]
                table_node.add("[yellow]表头:[/yellow] " + " | ".join(headers))

                # 显示数据行预览
                data_node = table_node.add("[green]数据预览:[/green]")
                for row_idx, row in enumerate(table.rows[1:6], 1):  # 只显示前5行数据
                    cells = [cell.text.strip() for cell in row.cells]
                    if any(cells):  # 跳过空行
                        data_node.add(f"第{row_idx}行: " + " | ".join(cells))

        # 显示文档结构树
        console.print()
        console.print(
            Panel(tree, title="[bold]文档结构和内容[/bold]", border_style="blue")
        )
        console.print()

    except Exception as e:
        console.print(f"[bold red]预览文件 {doc_path} 时出错: {e}[/bold red]")


def display_statistics(
    total_count: int, energy_saving_count: int, new_energy_count: int, output_file: str
) -> None:
    """Display processing statistics in a formatted table."""
    print("\n" + "=" * 50)
    print("处理统计报告".center(46))
    print("=" * 50)
    print(f"{'项目':^20}{'数值':^20}")
    print("-" * 50)
    print(f"{'总记录数':^20}{total_count:^20,}")
    print(f"{'节能型汽车':^20}{energy_saving_count:^20,}")
    print(f"{'新能源汽车':^20}{new_energy_count:^20,}")
    print(f"{'输出文件':^20}{output_file:^20}")
    print("=" * 50 + "\n")


def display_doc_content(
    doc_structure: Union[Dict[str, Any], list[str]],
    extra_info: Optional[Union[str, list[dict[str, str]]]] = None,
) -> None:
    """Display document structure in a tree format with enhanced formatting."""
    # 创建文档结构树
    tree = Tree("📄 文档结构")

    def add_to_tree(node: Dict[str, Any], tree_node: Tree) -> None:
        """递归添加节点到树中"""
        # 根据节点类型选择样式
        style_map = {
            "root": "white",
            "batch": "bold red",
            "section": "bold cyan",
            "subsection": "yellow",
            "subsubsection": "blue",
            "item": "magenta",
            "text": "white",
        }

        # 获取节点样式
        node_type = node.get("type", "text")
        style = style_map.get(node_type, "white")

        # 添加当前节点
        name = node.get("name", "")
        if name:
            child = tree_node.add(f"[{style}]{name}[/{style}]")
            # 递归添加子节点
            for sub_node in node.get("children", []):
                add_to_tree(sub_node, child)

    # 处理文档结构
    if isinstance(doc_structure, dict):
        add_to_tree(doc_structure, tree)
    else:
        # 如果是旧格式的列表，转换为新格式
        root_node = {
            "name": "文档内容",
            "type": "root",
            "children": [
                {"name": item, "type": "text", "children": []} for item in doc_structure
            ],
        }
        add_to_tree(root_node, tree)

    # 显示文档结构
    console.print("\n")
    console.print(Panel(tree, border_style="blue"))

    # 显示额外信息
    if isinstance(extra_info, list) and extra_info:
        # 按类型分组
        info_by_type: Dict[str, List[dict[str, str]]] = {}
        for info in extra_info:
            info_type = info.get("type", "其他")
            if info_type not in info_by_type:
                info_by_type[info_type] = []
            info_by_type[info_type].append(info)

        # 创建额外信息树
        extra_tree = Tree("📝 额外信息")
        for info_type, infos in info_by_type.items():
            type_node = extra_tree.add(f"[bold]{info_type}[/bold]")
            for info in infos:
                section = info.get("section", "未知章节")
                content = info.get("content", "")
                batch = info.get("batch", "")
                section_node = type_node.add(
                    f"[blue]{section}[/blue]"
                    + (f" [yellow](第{batch}批)[/yellow]" if batch else "")
                )

                # 对内容进行自动换行，确保每行不会太长
                wrapped_content = textwrap.fill(
                    content, width=100, break_long_words=False, break_on_hyphens=False
                )
                for line in wrapped_content.split("\n"):
                    section_node.add(line)

        console.print(Panel(extra_tree, border_style="green"))

    console.print()


def display_comparison(new_models: set[str], removed_models: set[str]):
    """
    显示型号对比结果
    """
    table = Table(title="型号对比", show_header=True, header_style="bold magenta")

    table.add_column("变更类型", style="dim")
    table.add_column("数量", justify="right")
    table.add_column("型号列表")

    # 添加新增型号
    if new_models:
        models_text = "\n".join(sorted(new_models))
        table.add_row("新增", str(len(new_models)), models_text)

    # 添加移除型号
    if removed_models:
        models_text = "\n".join(sorted(removed_models))
        table.add_row("移除", str(len(removed_models)), models_text)

    if new_models or removed_models:
        console.print()
        console.print(table)
        console.print()
    else:
        console.print("\n[green]没有型号变更[/green]\n")


@click.group()
def cli():
    """处理车辆数据文档的命令行工具"""
    pass


def extract_car_info(doc_path: str, verbose: bool = False) -> List[Dict[str, Any]]:
    """从docx文件中提取车辆信息"""
    processor = DocProcessor(doc_path)
    return processor.process()


@cli.command()
@click.argument(
    "input_path",
    type=click.Path(exists=True),  # 允许文件和目录
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False),
    default="cars_output.csv",
    help="输出CSV文件路径",
)
@click.option("-v", "--verbose", is_flag=True, help="显示详细处理信息")
@click.option("--preview", is_flag=True, help="显示文档内容预览")
@click.option(
    "--compare",
    type=click.Path(exists=True, dir_okay=False),
    help="与指定的CSV文件进行对比",
)
def process(
    input_path: str, output: str, verbose: bool, preview: bool, compare: str | None
) -> None:
    """处理指定的docx文件或目录下的所有docx文件"""
    process_files(input_path, output, verbose, preview, compare)


def get_memory_usage() -> str:
    """获取当前进程的内存使用情况"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    return f"{memory_info.rss / 1024 / 1024:.1f}MB"


def process_files(
    input_path: str,
    output: str,
    verbose: bool = False,
    preview: bool = False,
    compare: str | None = None,
) -> None:
    """处理指定的docx文件或目录下的所有docx文件的核心逻辑"""
    NodeType = dict[str, Union[str, list[dict[str, Any]]]]

    # 根据输入路径类型确定要处理的文件
    input_path_obj = Path(input_path)
    if input_path_obj.is_file():
        if input_path_obj.suffix.lower() != ".docx":
            console.print("[bold red]指定的文件不是docx文件")
            return
        doc_files = [input_path_obj]
    else:
        doc_files = list(input_path_obj.glob("*.docx"))

    if not doc_files:
        console.print("[bold red]未找到.docx文件")
        return

    # 显示文件预览
    if preview:
        for doc_file in doc_files:
            print_docx_content(str(doc_file))

    # 初始化数据存储
    all_cars_data = []
    doc_contents: list[NodeType] = []
    all_extra_info: list[dict[str, str]] = []

    # 创建进度显示
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        main_task = progress.add_task("[cyan]处理文件", total=len(doc_files))

        for doc_file in doc_files:
            try:
                start_time = time.time()
                if verbose:
                    progress.log(f"[bold]开始处理文件: {doc_file}")
                    progress.log(f"[dim]当前内存使用: {get_memory_usage()}[/dim]")

                # 提取文档内容和额外信息
                paragraphs, extra_info = extract_doc_content(str(doc_file))
                all_extra_info.extend(extra_info)

                # 处理车辆数据
                processor = DocProcessor(str(doc_file))
                cars = processor.process()

                # 收集处理后的数据
                if cars:
                    all_cars_data.extend(cars)

                # 清理内存
                del processor
                gc.collect()

                elapsed = time.time() - start_time
                if verbose:
                    progress.log(
                        f"[bold green]文件 {doc_file} 处理完成，耗时: {elapsed:.2f}秒[/bold green]"
                    )
                    progress.log(f"[dim]处理后内存使用: {get_memory_usage()}[/dim]")

                progress.advance(main_task)

            except Exception as e:
                progress.log(f"[bold red]处理文件 {doc_file} 时出错: {e}")

    # 创建根节点
    doc_tree = {"name": "文档内容", "type": "root", "children": doc_contents}

    # 显示统计和内容
    if all_cars_data:
        # 将收集的数据转换为DataFrame
        all_cars_df = pd.DataFrame(all_cars_data)

        # 设置列的顺序
        base_columns = [
            "batch",
            "car_type",
            "category",
            "sub_type",
            "序号",
            "企业名称",
            "品牌",
            "型号",
            "raw_text",
        ]
        all_columns = list(all_cars_df.columns)

        # 将其他列添加到基础列后面
        existing_columns = [col for col in base_columns if col in all_cars_df.columns]
        other_columns = [col for col in all_columns if col not in base_columns]
        final_columns = existing_columns + other_columns

        # 重新排列列并保存
        all_cars_df = all_cars_df[final_columns]
        all_cars_df.to_csv(output, index=False, encoding="utf-8-sig")

        # 显示统计和内容
        display_statistics(
            len(all_cars_df),
            len(all_cars_df[all_cars_df["car_type"] == 2]),
            len(all_cars_df[all_cars_df["car_type"] == 1]),
            output,
        )
        display_doc_content(doc_tree, all_extra_info)

        # 如果需要对比
        if compare:
            try:
                old_df = pd.read_csv(compare, encoding="utf-8-sig")
                new_models = set(all_cars_df["型号"].unique())
                old_models = set(old_df["型号"].unique())

                display_comparison(new_models - old_models, old_models - new_models)
            except Exception as e:
                console.print(f"[bold red]对比文件时出错: {e}")
    else:
        console.print("[bold red]未找到任何车辆记录")


@lru_cache(maxsize=32)
def load_document(doc_path: str) -> DocxDocument:
    """缓存加载的文档对象"""
    return Document(doc_path)


def profile_function(func):
    def wrapper(*args, **kwargs):
        profile = cProfile.Profile()
        try:
            return profile.runcall(func, *args, **kwargs)
        finally:
            s = StringIO()
            stats = pstats.Stats(profile, stream=s).sort_stats("cumulative")
            stats.print_stats(20)  # 显示前20个最耗时的函数调用
            console.print(f"\n[bold cyan]性能分析报告:[/bold cyan]\n{s.getvalue()}")

    return wrapper


class DocProcessor:
    """文档处理器类"""

    def __init__(self, doc_path: str):
        self.doc_path = doc_path
        self.start_time = time.time()
        self.doc: DocxDocument = load_document(doc_path)
        self.current_category: Optional[str] = None
        self.current_type: Optional[str] = None
        self.batch_number: Optional[str] = None
        self._table_cache: Dict[int, List[Dict[str, Any]]] = {}
        self.cars: List[Dict[str, Any]] = []
        self._processing_times: Dict[str, float] = {}
        self._chunk_size = 1000  # 分块处理的大小

    def _extract_table_cells_fast(self, table) -> List[List[str]]:
        """使用优化的方式提取表格内容"""
        rows = []
        for row in table._tbl.tr_lst:  # 直接访问内部XML结构
            cells = []
            for cell in row.tc_lst:
                # 直接获取文本内容
                text = "".join(node.text for node in cell.xpath(".//w:t"))
                cells.append(text.strip())
            if cells:  # 只添加非空行
                rows.append(cells)
        return rows

    def _extract_car_info(
        self, table_index: int, batch_number: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """从表格中提取车辆信息，使用优化的处理方式"""
        # 检查缓存
        if table_index in self._table_cache:
            return self._table_cache[table_index]

        start_time = time.time()
        table_cars: List[Dict[str, Any]] = []
        table = self.doc.tables[table_index]

        if not table or not table.rows:
            return table_cars

        # 使用快速方法提取所有单元格内容
        all_rows = self._extract_table_cells_fast(table)
        if not all_rows:
            return table_cars

        # 获取并处理表头
        headers = all_rows[0]
        if not headers or not any(headers):
            return table_cars

        # 根据表头判断表格类型
        table_category, table_type = get_table_type(
            headers, self.current_category, self.current_type
        )

        # 预先创建基础信息
        base_info = {
            "category": table_category,
            "sub_type": table_type,
            "car_type": 2 if table_category == "节能型" else 1,
            "batch": batch_number,
        }

        total_rows = len(all_rows) - 1
        if total_rows > 100:
            console.print(f"[dim]开始处理大表格，共 {total_rows} 行[/dim]")

        # 分块处理数据行
        for chunk_start in range(1, len(all_rows), self._chunk_size):
            chunk_end = min(chunk_start + self._chunk_size, len(all_rows))
            chunk_rows = all_rows[chunk_start:chunk_end]

            # 批量处理当前块的数据行
            for cells in chunk_rows:
                if len(cells) != len(headers):  # 跳过格式不匹配的行
                    continue

                # 创建新的字典，避免引用同一个对象
                car_info = base_info.copy()
                car_info["raw_text"] = " | ".join(cells)

                # 使用zip优化字段映射
                car_info.update(
                    {
                        header: clean_text(value)
                        for header, value in zip(headers, cells)
                        if value and header
                    }
                )

                # 处理车辆信息
                car_info = process_car_info(car_info, batch_number)

                # 验证数据
                is_valid, _ = validate_car_info(car_info)
                if is_valid:
                    table_cars.append(car_info)

            if total_rows > 100:
                progress = (chunk_end - 1) / total_rows * 100
                console.print(
                    f"[dim]处理进度: {progress:.1f}% ({chunk_end-1}/{total_rows})[/dim]"
                )

            # 主动触发垃圾回收
            if len(table_cars) > 5000:
                gc.collect()

        # 缓存结果
        self._table_cache[table_index] = table_cars

        # 记录处理时间
        elapsed = time.time() - start_time
        if total_rows > 100:
            console.print(
                f"[dim]表格 {table_index} 处理了 {total_rows} 行，耗时: {elapsed:.2f}秒[/dim]"
            )

        return table_cars

    def _log_time(self, operation: str) -> None:
        """记录操作耗时"""
        current_time = time.time()
        elapsed = current_time - self.start_time
        self._processing_times[operation] = elapsed
        if operation != "init":
            console.print(f"[dim]{operation} 耗时: {elapsed:.2f}秒[/dim]")
        self.start_time = current_time

    @profile_function
    def process(self) -> List[Dict[str, Any]]:
        """处理文档并返回所有车辆信息"""
        self._log_time("init")
        table_count = 0
        row_count = 0

        # 遍历文档中的所有元素
        for element in self.doc.element.body:
            # 处理段落
            if element.tag.endswith("p"):
                text = element.text.strip()
                if not text:
                    continue

                # 提取批次号
                if not self.batch_number:
                    self.batch_number = extract_batch_number(text)

                # 更新分类信息
                if "一、节能型汽车" in text:
                    self.current_category = "节能型"
                elif "二、新能源汽车" in text:
                    self.current_category = "新能源"
                elif text.startswith("（") and "）" in text:
                    self.current_type = text.strip()

            # 处理表格
            elif element.tag.endswith("tbl"):
                table_count += 1
                for i, table in enumerate(self.doc.tables):
                    if table._element is element:
                        if table.rows:
                            row_count += len(table.rows)
                        table_cars = self._extract_car_info(i, self.batch_number)
                        self.cars.extend(table_cars)
                        break

        self._log_time("process")
        console.print(f"[dim]处理了 {table_count} 个表格，共 {row_count} 行[/dim]")
        return self.cars


if __name__ == "__main__":
    cli()
