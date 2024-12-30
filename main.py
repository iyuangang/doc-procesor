from pathlib import Path
import pandas as pd
from docx import Document
import re
from typing import Dict, Any, Optional
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
)
from rich.syntax import Syntax
from rich.text import Text
from rich.tree import Tree
import textwrap


# 创建控制台对象
console = Console()


def cn_to_arabic(cn_num: str) -> str:
    """
    将中文数字转换为阿拉伯数字
    """
    if cn_num.isdigit():
        return cn_num

    cn_nums = {
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

    # 处理个位数
    if len(cn_num) == 1:
        return cn_nums.get(cn_num, cn_num)

    # 处理"百"开头的数字
    if "百" in cn_num:
        parts = cn_num.split("百")
        hundreds = int(cn_nums[parts[0]])
        if not parts[1]:  # 整百
            return str(hundreds * 100)
        return str(hundreds * 100 + int(cn_to_arabic(parts[1])))

    # 处理十位数
    if cn_num.startswith("十"):
        if len(cn_num) == 1:
            return "10"
        return "1" + cn_nums[cn_num[1]]

    # 处理带十的两位数
    if "十" in cn_num:
        parts = cn_num.split("十")
        tens = cn_nums[parts[0]]
        if len(parts) == 1 or not parts[1]:
            return f"{tens}0"
        ones = cn_nums[parts[1]]
        return f"{tens}{ones}"

    return cn_nums.get(cn_num, cn_num)


def extract_batch_number(text: str) -> Optional[str]:
    """
    从文本中提取批次号

    Args:
        text: 文本内容

    Returns:
        批次号或None
    """
    # 先尝试匹配完整的批次号格式
    match = re.search(r"第([一二三四五六七八九十百\d]+)批", text)
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
    if any(char in text for char in "一二三四五六七八九十百"):
        try:
            # 提取连续的中文数字
            match = re.search(r"([一二三四五六七八九十百]+)", text)
            if match:
                return cn_to_arabic(match.group(1))
        except (KeyError, ValueError):
            pass

    return None


def clean_text(text: str) -> str:
    """
    清理文本内容
    """
    # 移除多余的空白字符
    text = re.sub(r"\s+", " ", text.strip())
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
    headers: list[str], current_category: str, current_type: str
) -> tuple[str, str]:
    """
    根据表头判断表格类型
    """
    header_set = set(headers)

    # 定义各类型的特征字段
    type_features = {
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


def extract_car_info(doc_path: str, verbose: bool = False) -> list[dict[str, Any]]:
    """
    从docx文件中提取车辆信息

    Args:
        doc_path: docx文件路径
        verbose: 是否显示详细信息

    Returns:
        包含车辆信息的字典列表
    """
    doc = Document(doc_path)
    cars = []
    current_category = None
    current_type = None
    batch_number = None

    # 遍历文档中的所有元素
    for element in doc.element.body:
        # 处理段落
        if element.tag.endswith("p"):
            text = element.text.strip()
            if not text:
                continue

            # 提取批次号
            if not batch_number:
                batch_number = extract_batch_number(text)

            if "一、节能型汽车" in text:
                current_category = "节能型"
                if verbose:
                    click.echo(f"切换到分类: {current_category}")
            elif "二、新能源汽车" in text:
                current_category = "新能源"
                if verbose:
                    click.echo(f"切换到分类: {current_category}")
            elif text.startswith("（") and "）" in text:
                current_type = text.strip()
                if verbose:
                    click.echo(f"切换到子类型: {current_type}")

        # 处理表格
        elif element.tag.endswith("tbl"):
            table = None
            for t in doc.tables:
                if t._element is element:
                    table = t
                    break

            if not table or not table.rows:
                continue

            # 获取表头
            headers = [cell.text.strip() for cell in table.rows[0].cells]

            # 根据表头判断表格类型
            table_category, table_type = get_table_type(
                headers, current_category, current_type
            )
            if verbose:
                click.echo(f"\n处理表格 - 分类: {table_category}, 类型: {table_type}")

            # 处理数据行
            for row in table.rows[1:]:
                cells = [cell.text.strip() for cell in row.cells]
                if not cells or not any(cells):  # 跳过空行
                    continue

                car_info: dict[str, Any] = {
                    "raw_text": " | ".join(cells),
                    "category": table_category,
                    "sub_type": table_type,
                    "car_type": 2 if table_category == "节能型" else 1,
                }

                # 根据不同表格类型处理字段
                for i, header in enumerate(headers):
                    if i < len(cells) and cells[i]:
                        car_info[header] = cells[i]

                # 处理和标准化字段
                car_info = process_car_info(car_info, batch_number)

                # 验证数据
                is_valid, error_msg = validate_car_info(car_info)
                if is_valid:
                    cars.append(car_info)
                elif verbose:
                    click.echo(f"跳过无效数据: {error_msg}", err=True)

    return cars


def extract_doc_content(doc_path: str) -> tuple[list[str], list[dict[str, str]]]:
    """
    提取文档中除表格外的内容，并分离额外信息
    """
    doc = Document(doc_path)
    paragraphs: list[str] = []
    extra_info: list[dict[str, str]] = []
    current_section = None
    batch_found = False

    # 额外信息的标识词和对应类型
    info_types = {
        "勘误": "勘误",
        "关于": "政策",
        "符合": "说明",
        "技术要求": "说明",
        "自动转入": "说明",
    }

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # 检查批次号
        if not batch_found and "批" in text:
            batch_number = extract_batch_number(text)
            if batch_number:
                paragraphs.insert(0, text)  # 将批次号信息放在最前面
                batch_found = True
                continue

        # 识别主要分类
        if text.startswith("一、") or text.startswith("二、"):
            current_section = text
            paragraphs.append(text)
        # 识别子分类
        elif text.startswith("（"):
            current_section = text
            paragraphs.append(text)
        # 识别额外信息
        elif any(marker in text for marker in info_types.keys()):
            info_type = next((t for m, t in info_types.items() if m in text), "其他")
            extra_info.append(
                {
                    "section": current_section or "文档说明",
                    "type": info_type,
                    "content": text,
                }
            )
        else:
            paragraphs.append(text)

    return paragraphs, extra_info


def print_docx_content(doc_path: str):
    """
    打印文档内容预览
    """
    try:
        doc = Document(doc_path)
        console.print(f"\n[bold]文件: {doc_path}[/bold]")

        # 创建一个树形结构
        tree = Tree(f"📄 {Path(doc_path).name}")

        # 添加段落
        paragraphs_node = tree.add("📝 段落")
        for para in doc.paragraphs[:5]:  # 只显示前5个段落
            text = para.text.strip()
            if text:
                paragraphs_node.add(Text(textwrap.shorten(text, width=100)))

        # 添加表格
        tables_node = tree.add("📊 表格")
        for i, table in enumerate(doc.tables[:3]):  # 只显示前3个表格
            if table.rows:
                table_node = tables_node.add(f"表格 {i+1}")
                headers = [cell.text.strip() for cell in table.rows[0].cells]
                table_node.add("表头: " + " | ".join(headers))

        console.print(tree)
        console.print()
    except Exception as e:
        console.print(f"[bold red]预览文件 {doc_path} 时出错: {e}")


def display_statistics(df: pd.DataFrame, output_path: str):
    """
    显示处理统计信息
    """
    # 创建统计表格
    table = Table(
        title="处理统计",
        show_header=True,
        header_style="bold magenta",
        box=None,
    )

    table.add_column("项目", style="dim")
    table.add_column("数值", justify="right")

    # 添加统计数据
    total_records = len(df)
    energy_saving = len(df[df["car_type"] == 2])
    new_energy = len(df[df["car_type"] == 1])

    table.add_row("总记录数", str(total_records))
    table.add_row("节能型汽车", str(energy_saving))
    table.add_row("新能源汽车", str(new_energy))
    table.add_row("输出文件", output_path)

    # 显示统计表格
    console.print()
    console.print(table)
    console.print()


def display_doc_content(paragraphs: list[str], extra_info: list[dict[str, str]]):
    """
    显示文档结构和额外信息
    """
    # 创建文档结构树
    tree = Tree("📑 文档结构")
    current_main = None
    current_sub = None

    for para in paragraphs:
        if "批" in para and any(char in para for char in "一二三四五六七八九十百"):
            tree.add(f"🔢 {para}")
        elif para.startswith("一、") or para.startswith("二、"):
            current_main = tree.add(f"📂 {para}")
            current_sub = None
        elif para.startswith("（"):
            if current_main:
                current_sub = current_main.add(f"📁 {para}")
            else:
                current_sub = tree.add(f"📁 {para}")

    # 添加额外信息
    if extra_info:
        info_node = tree.add("ℹ️ 额外信息")
        for info in extra_info:
            section = info["section"] or "其他"
            content = textwrap.shorten(info["content"], width=100)
            info_node.add(f"[{info['type']}] {content}")

    # 显示文档结构
    console.print()
    console.print(Panel(tree, title="文档内容", border_style="blue"))
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


@cli.command()
@click.argument(
    "input_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True)
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
def process(input_dir: str, output: str, verbose: bool, preview: bool, compare: str):
    """处理指定目录下的所有docx文件"""
    doc_files = list(Path(input_dir).glob("*.docx"))

    if not doc_files:
        console.print("[bold red]未找到.docx文件")
        return

    # 显示文件预览
    if preview:
        for doc_file in doc_files:
            print_docx_content(str(doc_file))

    # 处理文件
    all_cars = []
    doc_contents = []
    all_extra_info = []

    # 创建一个新的控制台用于详细信息输出
    verbose_console = Console(stderr=True) if verbose else None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,  # 使进度条在完成后消失
    ) as progress:
        task = progress.add_task("处理文件", total=len(doc_files))

        for doc_file in doc_files:
            try:
                if verbose:
                    verbose_console.print(f"\n[bold]处理文件: {doc_file}")

                # 提取文档内容
                paragraphs, extra_info = extract_doc_content(str(doc_file))
                doc_contents.extend(paragraphs)
                all_extra_info.extend(extra_info)

                # 处理车辆数据
                cars = extract_car_info(str(doc_file), verbose)
                all_cars.extend(cars)

                progress.advance(task)
            except Exception as e:
                console.print(f"[bold red]处理文件 {doc_file} 时出错: {e}")

    console.print()  # 添加空行分隔

    # 创建DataFrame并保存为CSV
    if all_cars:
        df = pd.DataFrame(all_cars)
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
        # 获取所有列
        all_columns = list(df.columns)
        # 将其他列添加到基础列后面
        for col in all_columns:
            if col not in base_columns:
                base_columns.append(col)

        # 只保留存在的列
        existing_columns = [col for col in base_columns if col in df.columns]
        df = df[existing_columns]

        # 保存文件
        df.to_csv(output, index=False, encoding="utf-8-sig")

        # 显示统计和内容
        display_statistics(df, output)
        display_doc_content(doc_contents, all_extra_info)

        # 如果需要对比
        if compare:
            try:
                old_df = pd.read_csv(compare, encoding="utf-8-sig")
                new_models = set(df["型号"].unique())
                old_models = set(old_df["型号"].unique())

                display_comparison(new_models - old_models, old_models - new_models)
            except Exception as e:
                console.print(f"[bold red]对比文件时出错: {e}")
    else:
        console.print("[bold red]未找到任何车辆记录")


if __name__ == "__main__":
    cli()
