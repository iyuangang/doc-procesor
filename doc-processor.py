from pathlib import Path
import pandas as pd
from docx import Document
from docx.document import Document as DocxDocument
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
    "零": "0", "一": "1", "二": "2", "三": "3", "四": "4",
    "五": "5", "六": "6", "七": "7", "八": "8", "九": "9",
    "十": "10", "百": "100"
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
        self.standard_headers = [
            "表格编号", "分类", "car_type", "batch", "序号", "企业名称", "品牌", 
            "车辆型号", "排量(ml)", "额定载客人数(人)", "变速器", "整车整备质量(kg)", 
            "排放标准", "综合燃料消耗量(L/100km)", "商标", "产品名称", "燃料种类", 
            "最大设计总质量(kg)", "综合工况燃料消耗量(L/100km)", "准拖挂车总质量(kg)", 
            "产品型号", "纯电动续驶里程(km)", "燃料消耗量(L/100km)", "发动机排量(mL)", 
            "动力蓄电池总质量(kg)", "动力蓄电池总能量(kWh)", "备注", 
            "动力蓄电池组总质量(kg)", "动力蓄电池组总能量(kWh)", "发动机排量(mL)", 
            "燃料电池系统额定功率(kW)", "驱动电机额定功率(kW)"
        ]

    def _clean_text(self, text: str) -> str:
        """清理文本内容"""
        if not text:
            return ""
        # 统一空白字符
        text = re.sub(r'\s+', ' ', text.strip())
        # 统一单位格式
        text = text.replace('（', '(').replace('）', ')')
        # 移除重复的标点
        text = re.sub(r'[,，]{2,}', ',', text)
        # 统一国标格式
        text = re.sub(r'GB\s*([0-9.-]+)\s*国\s*Ⅵ', r'GB\1国Ⅵ', text)
        # 统一数值格式（处理类似"±5.1"这样的格式）
        text = re.sub(r'(\d+)\s*[±]\s*(\d+\.?\d*)', r'\1±\2', text)
        # 清理特殊字符
        text = text.replace('\n', ' ').replace('\r', ' ')
        return text

    def _standardize_header(self, header: str) -> str:
        """标准化表头名称"""
        header = self._clean_text(header)
        # 统一常见的表头变体
        header_mapping = {
            '型式 档位数': '变速器',
            '型式': '变速器',
            '通用名称': '品牌',
            '商标': '品牌',
            '发动机排量(ml)': '发动机排量(mL)',  # 统一单位大小写
            '额定载客人数（人）': '额定载客人数(人)',  # 统一括号格式
            '综合燃料消耗量（L/100km）': '综合燃料消耗量(L/100km)',
            '最大设计总质量（kg）': '最大设计总质量(kg)',
            '准拖挂车总质量（kg）': '准拖挂车总质量(kg)',
            '整车整备质量（kg）': '整车整备质量(kg)',
            '纯电动续驶里程（km）': '纯电动续驶里程(km)',
            '动力蓄电池总质量（kg）': '动力蓄电池总质量(kg)',
            '动力蓄电池组总质量（kg）': '动力蓄电池组总质量(kg)'
        }
        return header_mapping.get(header, header)

    def _validate_row_data(self, row_dict: Dict[str, Any]) -> bool:
        """验证行数据的有效性"""
        # 必填字段验证
        required_fields = ['表格编号', '分类', 'car_type', 'batch', '序号', '企业名称']
        if not all(row_dict.get(field) for field in required_fields):
            return False
            
        # 数值字段验证
        numeric_fields = [
            '排量(ml)', '整车整备质量(kg)', '最大设计总质量(kg)',
            '纯电动续驶里程(km)', '动力蓄电池总质量(kg)', 
            '动力蓄电池总能量(kWh)', '燃料电池系统额定功率(kW)',
            '驱动电机额定功率(kW)'
        ]
        for field in numeric_fields:
            if row_dict.get(field):
                try:
                    # 处理可能包含±的数值
                    value = row_dict[field].split('±')[0]
                    float(value.replace(',', ''))
                except ValueError:
                    row_dict[field] = ''  # 无效数值置空
                    
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
        car_type_stats = df['car_type'].value_counts()
        console.print(f"节能型(2): {car_type_stats.get(2, 0)}行")
        console.print(f"新能源(1): {car_type_stats.get(1, 0)}行")
        
        # 批次统计
        batch_stats = df['batch'].value_counts().sort_index()
        console.print("\n批次分布:")
        for batch, count in batch_stats.items():
            console.print(f"第{batch}批: {count}行")
        
        # 企业统计
        company_stats = df['企业名称'].value_counts()
        console.print(f"\n涉及企业数量: {len(company_stats)}")
        
        # 燃料类型统计
        if '燃料种类' in df.columns:
            fuel_stats = df['燃料种类'].value_counts()
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
            console=console
        ) as progress:
            task = progress.add_task("[cyan]处理表格数据...", total=len(self.tables_info))

            for table_info in self.tables_info:
                if not table_info.get("data_rows"):
                    progress.advance(task)
                    continue

                headers = table_info["headers"]
                for row in table_info["data_rows"]:
                    # 创建基础数据字典
                    row_dict = {
                        "表格编号": table_info["table_index"],
                        "分类": table_info["category"],
                        "car_type": table_info["car_type"],
                        "batch": table_info["batch"]
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
            
            # 重排列顺序
            columns = [h for h in self.standard_headers if h in df.columns]
            df = df[columns]
            
            # 最终清理
            for col in df.columns:
                if pd.api.types.is_object_dtype(df[col]):  # 使用pandas API检查数据类型
                    df[col] = df[col].apply(self._clean_text)

            # 保存文件
            df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
            # 显示统计信息
            console.print(f"[green]数据已保存到: {output_path}[/green]")
            console.print(f"[blue]总共处理了 {len(df)} 行数据[/blue]")
            
            # 打印详细统计信息
            self._print_statistics(df)
        else:
            console.print("[red]没有找到可导出的数据[/red]")

    def process_document(self) -> None:
        """处理文档，识别分类和表格"""
        start_time = time.time()
        console.print(f"\n[cyan]开始处理文档: {self.doc_path}[/cyan]")

        # 遍历文档元素
        for element in self.doc.element.body:
            # 处理段落，识别分类
            if element.tag.endswith("p"):
                text = element.text.strip()
                if not text:
                    continue

                # 提取批次号
                if "批" in text and not self.batch_number:
                    batch_num = self._extract_batch_number(text)
                    if batch_num:
                        self.batch_number = batch_num
                        console.print(f"[green]识别到批次号: {self.batch_number}[/green]")

                # 识别分类
                if "一、节能型汽车" in text:
                    self.current_category = "节能型"
                    self.current_car_type = 2  # 节能型标记为2
                    console.print("[blue]识别到节能型汽车分类[/blue]")
                elif "二、新能源汽车" in text:
                    self.current_category = "新能源"
                    self.current_car_type = 1  # 新能源标记为1
                    console.print("[blue]识别到新能源汽车分类[/blue]")

            # 处理表格
            elif element.tag.endswith("tbl"):
                for i, table in enumerate(self.doc.tables):
                    if table._element is element:
                        table_info = self._get_table_info(i, table)
                        if table_info:
                            self.tables_info.append(table_info)
                        break

        console.print(f"[green]文档处理完成，耗时: {time.time() - start_time:.2f}秒[/green]")

    def _get_table_info(self, table_index: int, table) -> Dict[str, Any]:
        """获取表格的基本信息"""
        rows = self._extract_table_cells_fast(table)
        if not rows:
            return {}

        # 标准化表头
        headers = [self._standardize_header(h) for h in rows[0]]
        
        return {
            "table_index": table_index + 1,
            "category": self.current_category,
            "car_type": self.current_car_type,
            "batch": self.batch_number,
            "headers": headers,
            "row_count": len(rows) - 1,
            "data_rows": rows[1:] if len(rows) > 1 else []
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
    for doc_file in doc_files:
        processor = DocProcessor(str(doc_file))
        processor.process_document()
        all_tables_info.extend(processor.tables_info)
        
        # 清理内存
        del processor
        gc.collect()

    # 如果有多个文件，合并处理结果
    if all_tables_info:
        processor = DocProcessor(str(doc_files[0]))  # 创建一个处理器用于导出
        processor.tables_info = all_tables_info
        processor.export_to_csv(output_path)
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
