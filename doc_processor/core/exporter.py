"""
数据导出器模块
"""

import csv
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union, Tuple

import pandas as pd

from doc_processor.exceptions import ProcessingError
from doc_processor.models import CarInfoCollection
from doc_processor.utils import create_logger, print_success

# 创建日志记录器
logger = create_logger(__name__)


class DataExporter:
    """
    数据导出器类，将车辆信息导出为多种格式

    Attributes:
        encoding: 文件编码
        delimiter: CSV分隔符
    """

    def __init__(self, encoding: str = "utf-8-sig", delimiter: str = ",") -> None:
        """
        初始化数据导出器

        Args:
            encoding: 文件编码
            delimiter: CSV分隔符
        """
        self.encoding = encoding
        self.delimiter = delimiter

    def export_to_csv(
        self,
        data: Union[CarInfoCollection, List[Dict[str, Any]]],
        output_path: Union[str, Path],
        include_headers: bool = True,
    ) -> None:
        """
        导出数据为CSV格式

        Args:
            data: 要导出的数据
            output_path: 输出文件路径
            include_headers: 是否包含表头

        Raises:
            ProcessingError: 导出数据出错
        """
        try:
            # 确保输出目录存在
            output_dir = os.path.dirname(str(output_path))
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 将数据转换为字典列表
            if isinstance(data, CarInfoCollection):
                records = data.to_list_of_dicts()
            else:
                records = data

            if not records:
                logger.warning(f"没有数据可导出到: {output_path}")
                return

            # 获取所有可能的字段
            all_fields = set()
            for record in records:
                all_fields.update(record.keys())

            # 排序字段，使关键字段在前面
            priority_fields = [
                "batch",
                "car_type",
                "category",
                "sub_type",
                "序号",
                "企业名称",
                "品牌",
                "型号",
            ]
            fields = priority_fields + [
                f for f in sorted(all_fields) if f not in priority_fields
            ]

            # 使用CSV模块写入数据
            with open(output_path, "w", newline="", encoding=self.encoding) as f:
                writer = csv.DictWriter(f, fieldnames=fields, delimiter=self.delimiter)

                # 写入表头
                if include_headers:
                    writer.writeheader()

                # 写入数据
                for record in records:
                    writer.writerow(record)

            logger.info(f"成功导出 {len(records)} 条记录到: {output_path}")
            print_success(f"成功导出 {len(records)} 条记录到: {output_path}")

        except Exception as e:
            logger.error(f"导出CSV失败: {output_path}", exc_info=True)
            raise ProcessingError(f"导出CSV失败: {str(e)}")

    def compare_model_changes(
        self, new_data: CarInfoCollection, old_data_path: Union[str, Path]
    ) -> Tuple[Set[str], Set[str]]:
        """
        比较新旧数据的型号变化

        Args:
            new_data: 新数据
            old_data_path: 旧数据文件路径

        Returns:
            新增型号和删除型号的集合元组

        Raises:
            ProcessingError: 比较数据出错
        """
        try:
            # 获取新数据的型号集合
            new_models = set(new_data.get_models())

            # 读取旧数据
            if not os.path.exists(old_data_path):
                return new_models, set()

            try:
                # 使用pandas读取CSV文件
                df = pd.read_csv(
                    old_data_path, encoding=self.encoding, delimiter=self.delimiter
                )
                if "型号" not in df.columns:
                    logger.warning(f"旧数据文件不包含'型号'字段: {old_data_path}")
                    return new_models, set()

                # 获取旧数据的型号集合
                old_models = set(df["型号"].dropna().astype(str).unique())

                # 计算新增和删除的型号
                added_models = new_models - old_models
                removed_models = old_models - new_models

                return added_models, removed_models

            except Exception as e:
                logger.error(f"读取旧数据文件出错: {old_data_path}", exc_info=True)
                return new_models, set()

        except Exception as e:
            logger.error("比较型号变化出错", exc_info=True)
            raise ProcessingError(f"比较型号变化出错: {str(e)}")

    def merge_collections(
        self, collections: List[CarInfoCollection]
    ) -> CarInfoCollection:
        """
        合并多个车辆信息集合

        Args:
            collections: 车辆信息集合列表

        Returns:
            合并后的车辆信息集合
        """
        merged = CarInfoCollection()
        for collection in collections:
            for car in collection.cars:
                merged.add(car)
        return merged
