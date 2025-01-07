from pathlib import Path
import pandas as pd
from docx import Document
from docx.document import Document as DocxDocument
from docx.table import Table as DocxTable
import re
from typing import Dict, Any, Optional, List, Union
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
import time
import gc
from functools import lru_cache

# 创建控制台对象用于美化输出
console = Console()

# 预编译正则表达式
BATCH_NUMBER_PATTERN = re.compile(r"第([一二三四五六七八九十百零\d]+)批")
WHITESPACE_PATTERN = re.compile(r"\s+")

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
    """将中文数字转换为阿拉伯数字"""
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


class DocProcessor:
    """文档处理器类"""

    def __init__(self, doc_path: str):
        self.doc_path = doc_path
        self.doc: DocxDocument = Document(doc_path)
        self.current_category: Optional[str] = None  # 当前分类（节能型/新能源）
        self.current_car_type: int = 0  # 2表示节能型，1表示新能源
        self.batch_number: Optional[str] = None
        self.tables_info: List[Dict[str, Any]] = []  # 存储表格信息
        self._chunk_size = 1000  # 分块处理大小
        self.doc_structure: Dict[str, Any] = {
            "batch_number": None,
            "sections": [],
            "tables": [],
            "notices": [],  # 政策说明
            "corrections": [],  # 勘误信息
            "other_info": [],  # 其他重要信息
        }
        self.standard_headers = [
            "表格编号",
            "分类",
            "car_type",
            "batch",
            "序号",
            "企业名称",
            "品牌",
            "车辆型号",
            "排量(ml)",
            "额定载客人数(人)",
            "变速器",
            "整车整备质量(kg)",
            "排放标准",
            "综合燃料消耗量(L/100km)",
            "商标",
            "产品名称",
            "燃料种类",
            "最大设计总质量(kg)",
            "综合工况燃料消耗量(L/100km)",
            "准拖挂车总质量(kg)",
            "产品型号",
            "纯电动续驶里程(km)",
            "燃料消耗量(L/100km)",
            "发动机排量(mL)",
            "动力蓄电池总质量(kg)",
            "动力蓄电池总能量(kWh)",
            "备注",
            "动力蓄电池组总质量(kg)",
            "动力蓄电池组总能量(kWh)",
            "发动机排量(mL)",
            "燃料电池系统额定功率(kW)",
            "驱动电机额定功率(kW)",
        ]

    def _clean_text(self, text: str) -> str:
        """清理文本内容"""
        if not text:
            return ""
        # 统一空白字符
        text = re.sub(r"\s+", " ", text.strip())
        # 统一单位格式
        text = text.replace("（", "(").replace("）", ")")
        # 移除重复的标点
        text = re.sub(r"[,，]{2,}", ",", text)
        # 统一国标格式
        text = re.sub(r"GB\s*([0-9.-]+)\s*国\s*Ⅵ", r"GB\1国Ⅵ", text)
        # 统一数值格式（处理类似"±5.1"这样的格式）
        text = re.sub(r"(\d+)\s*[±]\s*(\d+\.?\d*)", r"\1±\2", text)
        # 清理特殊字符
        text = text.replace("\n", " ").replace("\r", " ")
        return text

    def _standardize_header(self, header: str) -> str:
        """标准化表头名称"""
        header = self._clean_text(header)
        # 统一常见的表头变体
        header_mapping = {
            "型式 档位数": "变速器",
            "型式": "变速器",
            "通用名称": "品牌",
            "商标": "品牌",
            "发动机排量(ml)": "发动机排量(mL)",  # 统一单位大小写
            "额定载客人数（人）": "额定载客人数(人)",  # 统一括号格式
            "综合燃料消耗量（L/100km）": "综合燃料消耗量(L/100km)",
            "最大设计总质量（kg）": "最大设计总质量(kg)",
            "准拖挂车总质量（kg）": "准拖挂车总质量(kg)",
            "整车整备质量（kg）": "整车整备质量(kg)",
            "纯电动续驶里程（km）": "纯电动续驶里程(km)",
            "动力蓄电池总质量（kg）": "动力蓄电池总质量(kg)",
            "动力蓄电池组总质量（kg）": "动力蓄电池组总质量(kg)",
        }
        return header_mapping.get(header, header)

    def _validate_row_data(self, row_dict: Dict[str, Any]) -> bool:
        """验证行数据的有效性"""
        # 必填字段验证
        required_fields = ["表格编号", "分类", "car_type", "batch", "序号", "企业名称"]
        if not all(row_dict.get(field) for field in required_fields):
            return False

        # 数值字段验证
        numeric_fields = [
            "排量(ml)",
            "整车整备质量(kg)",
            "最大设计总质量(kg)",
            "纯电动续驶里程(km)",
            "动力蓄电池总质量(kg)",
            "动力蓄电池总能量(kWh)",
            "燃料电池系统额定功率(kW)",
            "驱动电机额定功率(kW)",
        ]
        for field in numeric_fields:
            if row_dict.get(field):
                try:
                    # 处理可能包含±的数值
                    value = row_dict[field].split("±")[0]
                    float(value.replace(",", ""))
                except ValueError:
                    row_dict[field] = ""  # 无效数值置空

        return True

    def _extract_table_cells_fast(self, table) -> List[List[str]]:
        """快速提取表格内容的优化方法"""
        rows = []
        last_company = ""
        last_brand = ""

        for row in table._tbl.tr_lst:
            cells = []
            for cell in row.tc_lst:
                # 提取并清理文本
                text = "".join(node.text for node in cell.xpath(".//w:t"))
                text = self._clean_text(text)
                cells.append(text)

            if any(cells):  # 跳过完全空行
                # 处理企业名称的延续性
                if len(cells) > 1:
                    if not cells[1] and last_company:
                        cells[1] = last_company
                    elif cells[1]:
                        last_company = cells[1]

                # 处理品牌的延续性
                if len(cells) > 2:
                    if not cells[2] and last_brand:
                        cells[2] = last_brand
                    elif cells[2]:
                        last_brand = cells[2]

                rows.append(cells)
        return rows

    def _print_statistics(self, df: pd.DataFrame) -> None:
        """打印详细的数据统计信息"""
        console.print("\n[cyan]数据统计:[/cyan]")
        console.print(f"总记录数: {len(df)}")

        # 车型统计
        car_type_stats = df["car_type"].value_counts()
        console.print(f"节能型(2): {car_type_stats.get(2, 0)}行")
        console.print(f"新能源(1): {car_type_stats.get(1, 0)}行")

        # 批次统计
        batch_stats = df["batch"].value_counts().sort_index()
        console.print("\n批次分布:")
        for batch, count in batch_stats.items():
            console.print(f"第{batch}批: {count}行")

        # 企业统计
        company_stats = df["企业名称"].value_counts()
        console.print(f"\n涉及企业数量: {len(company_stats)}")

        # 燃料类型统计
        if "燃料种类" in df.columns:
            fuel_stats = df["燃料种类"].value_counts()
            console.print("\n燃料类型分布:")
            for fuel, count in fuel_stats.items():
                if fuel:  # 只显示非空值
                    console.print(f"{fuel}: {count}行")

    def export_to_csv(self, output_path: str) -> None:
        """将表格信息导出到CSV文件"""
        all_data = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]处理表格数据...", total=len(self.tables_info)
            )

            for table_info in self.tables_info:
                if not table_info.get("data_rows"):
                    progress.advance(task)
                    continue

                headers = table_info["headers"]
                batch = table_info.get("batch")
                if not batch:
                    console.print(
                        f"[yellow]警告: 表格 {table_info['table_index']} 没有批次号[/yellow]"
                    )
                    continue

                for row in table_info["data_rows"]:
                    # 创建基础数据字典
                    row_dict = {
                        "表格编号": table_info["table_index"],
                        "分类": table_info["category"],
                        "car_type": table_info["car_type"],
                        "batch": batch,  # 确保批次号被正确设置
                    }

                    # 添加表格数据
                    for i, header in enumerate(headers):
                        if i < len(row):
                            value = self._clean_text(row[i])
                            row_dict[header] = value

                    # 确保所有标准字段都存在
                    for header in self.standard_headers:
                        if header not in row_dict:
                            row_dict[header] = ""

                    # 验证和添加数据
                    if self._validate_row_data(row_dict):
                        all_data.append(row_dict)

                progress.advance(task)

        # 转换为DataFrame并保存
        if all_data:
            df = pd.DataFrame(all_data)

            # 确保批次号是整数类型
            df["batch"] = (
                pd.to_numeric(df["batch"], errors="coerce").fillna(0).astype(int)
            )

            # 重排列顺序
            columns = [h for h in self.standard_headers if h in df.columns]
            df = df[columns]

            # 最终清理
            for col in df.columns:
                if pd.api.types.is_object_dtype(df[col]):
                    df[col] = df[col].apply(self._clean_text)

            # 保存文件
            df.to_csv(output_path, index=False, encoding="utf-8-sig")

            # 显示统计信息
            console.print(f"[green]数据已保存到: {output_path}[/green]")
            console.print(f"[blue]总共处理了 {len(df)} 行数据[/blue]")

            # 打印详细统计信息
            self._print_statistics(df)
        else:
            console.print("[red]没有找到可导出的数据[/red]")

    def _analyze_paragraph(self, text: str, style_name: str = "Normal") -> None:
        """分析段落内容，提取结构信息"""
        text = text.strip()
        if not text:
            return

        # 提取批次号
        if "批" in text and not self.doc_structure["batch_number"]:
            batch_num = self._extract_batch_number(text)
            if batch_num:
                self.doc_structure["batch_number"] = batch_num
                self.batch_number = batch_num

        # 识别主要分类
        if "一、节能型汽车" in text:
            self.current_category = "节能型"
            self.current_car_type = 2
            self.doc_structure["sections"].append(
                {
                    "type": "main_section",
                    "category": "节能型",
                    "car_type": 2,
                    "title": text,
                    "subsections": [],
                }
            )
        elif "二、新能源汽车" in text:
            self.current_category = "新能源"
            self.current_car_type = 1
            self.doc_structure["sections"].append(
                {
                    "type": "main_section",
                    "category": "新能源",
                    "car_type": 1,
                    "title": text,
                    "subsections": [],
                }
            )
        # 识别子分类（通常以括号开头）
        elif text.startswith("（") and "）" in text:
            if self.doc_structure["sections"]:
                self.doc_structure["sections"][-1]["subsections"].append(
                    {"type": "sub_section", "title": text}
                )

        # 识别政策说明和勘误
        elif any(keyword in text for keyword in ["关于", "政策", "要求", "说明"]):
            self.doc_structure["notices"].append({"type": "policy", "content": text})
        elif "勘误" in text or "更正" in text:
            self.doc_structure["corrections"].append(
                {"type": "correction", "content": text}
            )
        elif any(keyword in text for keyword in ["注意", "特别说明", "重要"]):
            self.doc_structure["other_info"].append(
                {"type": "important_notice", "content": text}
            )

    def _analyze_table(self, table_index: int, table: DocxTable) -> None:
        """分析表格结构"""
        rows = self._extract_table_cells_fast(table)
        if not rows:
            return

        headers = [self._standardize_header(h) for h in rows[0]]
        table_info = {
            "table_index": table_index + 1,
            "category": self.current_category,
            "car_type": self.current_car_type,
            "headers": headers,
            "row_count": len(rows) - 1,
            "sample_data": rows[1] if len(rows) > 1 else None,
        }

        # 根据表头和数据推断表格类型
        table_type = self._infer_table_type(headers, rows)
        table_info["table_type"] = table_type

        self.doc_structure["tables"].append(table_info)

    def _infer_table_type(self, headers: List[str], rows: List[List[str]]) -> str:
        """推断表格类型"""
        header_set = set(headers)

        # 检查特征字段
        if "纯电动续驶里程(km)" in header_set:
            return "纯电动汽车"
        elif "燃料电池系统额定功率(kW)" in header_set:
            return "燃料电池汽车"
        elif "动力蓄电池总能量(kWh)" in header_set and "发动机排量(mL)" in header_set:
            return "插电式混合动力汽车"
        elif "排量(ml)" in header_set and "额定载客人数(人)" in header_set:
            return "节能型乘用车"
        elif "整车整备质量(kg)" in header_set and "燃料种类" in header_set:
            # 进一步区分商用车类型
            if rows and len(rows) > 1:
                sample_data = rows[1]
                fuel_type_index = headers.index("燃料种类")
                if len(sample_data) > fuel_type_index:
                    fuel_type = sample_data[fuel_type_index]
                    if "CNG" in fuel_type:
                        return "节能型轻型商用车(CNG)"
                    elif "柴油" in fuel_type:
                        return "节能型轻型商用车(柴油)"
                    elif "LNG" in fuel_type:
                        return "节能型重型商用车"

        return "其他"

    def print_doc_structure(self) -> None:
        """打印文档结构"""
        console.print(f"\n[cyan]文档结构分析: {self.doc_path}[/cyan]")

        # 打印批次信息
        if self.doc_structure["batch_number"]:
            console.print(
                f"[yellow]批次: 第{self.doc_structure['batch_number']}批[/yellow]"
            )

        # 打印主要分类和子分类
        for section in self.doc_structure["sections"]:
            console.print(f"\n[bold green]{section['title']}[/bold green]")
            for subsection in section.get("subsections", []):
                console.print(f"  [green]{subsection['title']}[/green]")

        # 打印表格信息
        console.print("\n[bold blue]表格结构:[/bold blue]")
        for table in self.doc_structure["tables"]:
            console.print(
                f"  表格 {table['table_index']}: [yellow]{table['table_type']}[/yellow]"
            )
            console.print(
                f"    分类: {table['category']} (car_type: {table['car_type']})"
            )
            console.print(f"    记录数: {table['row_count']}")
            if table.get("sample_data"):
                console.print(
                    "    示例数据: "
                    + " | ".join(str(x) for x in table["sample_data"][:3])
                    + "..."
                )

        # 打印政策说明和勘误
        if self.doc_structure["notices"]:
            console.print("\n[bold magenta]政策说明:[/bold magenta]")
            for notice in self.doc_structure["notices"]:
                console.print(f"  • {notice['content']}")

        if self.doc_structure["corrections"]:
            console.print("\n[bold red]勘误信息:[/bold red]")
            for correction in self.doc_structure["corrections"]:
                console.print(f"  • {correction['content']}")

        if self.doc_structure["other_info"]:
            console.print("\n[bold yellow]其他重要信息:[/bold yellow]")
            for info in self.doc_structure["other_info"]:
                console.print(f"  • {info['content']}")

    def process_document(self) -> None:
        """处理文档，识别分类和表格"""
        start_time = time.time()
        console.print(f"\n[cyan]开始处理文档: {self.doc_path}[/cyan]")

        # 重置批次号
        self.batch_number = None
        self.doc_structure["batch_number"] = None

        # 首先扫描文档寻找批次号
        for element in self.doc.element.body:
            if element.tag.endswith("p"):
                text = element.text.strip()
                if text and "批" in text:
                    batch_num = self._extract_batch_number(text)
                    if batch_num:
                        self.batch_number = batch_num
                        self.doc_structure["batch_number"] = batch_num
                        console.print(
                            f"[green]识别到批次号: {self.batch_number}[/green]"
                        )
                        break

        # 如果没有找到批次号，尝试从文件名中提取
        if not self.batch_number:
            file_name = Path(self.doc_path).stem
            if file_name.isdigit():
                self.batch_number = file_name
                self.doc_structure["batch_number"] = file_name
                console.print(
                    f"[yellow]从文件名识别到批次号: {self.batch_number}[/yellow]"
                )

        # 继续处理文档其他部分
        for element in self.doc.element.body:
            if element.tag.endswith("p"):
                text = element.text.strip()
                if text:
                    self._analyze_paragraph(text)
            elif element.tag.endswith("tbl"):
                for i, table in enumerate(self.doc.tables):
                    if table._element is element:
                        self._analyze_table(i, table)
                        table_info = self._get_table_info(i, table)
                        if table_info:
                            # 确保每个表格都有批次号
                            if not table_info.get("batch"):
                                table_info["batch"] = self.batch_number
                            self.tables_info.append(table_info)
                        break

        # 打印文档结构
        self.print_doc_structure()

        console.print(
            f"[green]文档处理完成，耗时: {time.time() - start_time:.2f}秒[/green]"
        )

    def _get_table_info(self, table_index: int, table) -> Dict[str, Any]:
        """获取表格的基本信息"""
        rows = self._extract_table_cells_fast(table)
        if not rows:
            return {}

        # 标准化表头
        headers = [self._standardize_header(h) for h in rows[0]]

        # 确保批次号被正确设置
        if not self.batch_number:
            console.print("[yellow]警告: 表格处理时未找到批次号[/yellow]")

        return {
            "table_index": table_index + 1,
            "category": self.current_category,
            "car_type": self.current_car_type,
            "batch": self.batch_number,  # 这里可能是问题所在
            "headers": headers,
            "row_count": len(rows) - 1,
            "data_rows": rows[1:] if len(rows) > 1 else [],
        }

    def _extract_batch_number(self, text: str) -> Optional[str]:
        """从文本中提取并转换批次号"""
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
        return None

    def verify_csv_batch_distribution(self, csv_path: str) -> None:
        """验证CSV文件中的批次分布"""
        try:
            df = pd.read_csv(csv_path, encoding="utf-8-sig")

            # 批次分布统计
            batch_stats = df["batch"].value_counts().sort_index()

            console.print("\n[bold cyan]CSV文件批次分布验证:[/bold cyan]")
            console.print(f"CSV文件中的总记录数: {len(df)}")
            console.print("\n批次分布详情:")
            for batch, count in batch_stats.items():
                console.print(f"第{int(batch)}批: {count}行")

            # 检查是否有缺失的批次
            all_batches = set(
                range(int(batch_stats.index.min()), int(batch_stats.index.max()) + 1)
            )
            missing_batches = all_batches - set(batch_stats.index)
            if missing_batches:
                console.print("\n[red]警告: 以下批次在CSV中缺失:[/red]")
                for batch in sorted(missing_batches):
                    console.print(f"第{batch}批")

            # 验证每个批次的数据完整性
            console.print("\n[cyan]批次数据完整性检查:[/cyan]")
            for batch in batch_stats.index:
                batch_data = df[df["batch"] == batch]
                empty_fields = batch_data.isna().sum()
                if (empty_fields > 0).any():
                    console.print(f"\n第{int(batch)}批数据质量报告:")
                    for field, count in empty_fields[empty_fields > 0].items():
                        console.print(f"  {field}: {count}个空值")

        except Exception as e:
            console.print(f"[red]验证CSV文件时出错: {str(e)}[/red]")


def process_files(input_path: str, output_path: str = "tables_output.csv"):
    """处理指定路径的文件"""
    input_path_obj = Path(input_path)

    # 确定要处理的文件
    if input_path_obj.is_file():
        if input_path_obj.suffix.lower() != ".docx":
            console.print("[red]指定的文件不是docx文件[/red]")
            return
        doc_files = [input_path_obj]
    else:
        doc_files = list(input_path_obj.glob("*.docx"))

    if not doc_files:
        console.print("[red]未找到.docx文件[/red]")
        return

    # 处理所有文件
    all_tables_info = []
    batch_info = {}  # 用于记录每个批次的数据量

    for doc_file in doc_files:
        processor = DocProcessor(str(doc_file))
        processor.process_document()

        # 记录每个批次的数据量
        batch = processor.batch_number
        if batch:
            total_records = sum(
                table.get("row_count", 0) for table in processor.tables_info
            )
            batch_info[batch] = {
                "file": doc_file.name,
                "total_records": total_records,
                "tables_count": len(processor.tables_info),
            }
            console.print(f"[cyan]批次 {batch} 统计:[/cyan]")
            console.print(f"  文件: {doc_file.name}")
            console.print(f"  表格数: {len(processor.tables_info)}")
            console.print(f"  记录数: {total_records}")
        else:
            console.print(f"[red]警告: {doc_file.name} 未能识别批次号[/red]")

        all_tables_info.extend(processor.tables_info)

        # 清理内存
        del processor
        gc.collect()

    # 如果有多个文件，合并处理结果
    if all_tables_info:
        processor = DocProcessor(str(doc_files[0]))
        processor.tables_info = all_tables_info

        # 打印批次汇总信息
        console.print("\n[bold cyan]批次汇总信息:[/bold cyan]")
        for batch, info in sorted(batch_info.items()):
            console.print(f"批次 {batch}:")
            console.print(f"  文件: {info['file']}")
            console.print(f"  表格数: {info['tables_count']}")
            console.print(f"  记录数: {info['total_records']}")

        processor.export_to_csv(output_path)

        # 添加CSV验证
        processor.verify_csv_batch_distribution(output_path)
    else:
        console.print("[red]未找到任何表格数据[/red]")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        console.print("[red]请指定要处理的文件或目录路径[/red]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "tables_output.csv"

    process_files(input_path, output_path)
