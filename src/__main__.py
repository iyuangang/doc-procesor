"""
文档处理器主程序入口
用于提供命令行接口，处理文档并生成结果
"""

import argparse
import glob
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import pandas as pd

from rich.progress import TaskID

from .batch.validator import calculate_statistics
from .config.settings import setup_logging, load_config, Settings
from .models.car_info import BatchInfo, CarInfo
from .processor.doc_processor import DocProcessor, process_doc
from .ui.console import display_statistics, create_progress_bar


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="车辆信息文档处理器")

    parser.add_argument("input", help="输入文件路径或目录")
    parser.add_argument("-o", "--output", help="输出文件路径或目录", default="output")
    parser.add_argument("-c", "--config", help="配置文件路径", default="config.yaml")
    parser.add_argument(
        "-l", "--log-config", help="日志配置文件路径", default="logging.yaml"
    )
    parser.add_argument("-v", "--verbose", help="显示详细信息", action="store_true")
    parser.add_argument("--chunk-size", help="数据处理块大小", type=int, default=1000)
    parser.add_argument("--skip-verification", help="跳过批次验证", action="store_true")
    parser.add_argument(
        "--pattern", help="文件匹配模式 (仅当输入为目录时有效)", default="*.docx"
    )

    return parser.parse_args()


def process_single_file(
    file_path: str, output_dir: str, config: Dict[str, Any], verbose: bool = False
) -> List[Dict[str, Any]]:
    """
    处理单个文件

    Args:
        file_path: 文件路径
        output_dir: 输出目录
        config: 配置信息
        verbose: 是否显示详细信息

    Returns:
        处理结果列表
    """
    logger = logging.getLogger(__name__)

    start_time = time.time()
    logger.info(f"处理文件: {file_path}")

    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return []

    try:
        # 创建处理器并处理文档
        processor = DocProcessor(file_path, verbose=verbose, config=config)
        cars = processor.process()

        if not cars:
            logger.warning(f"未提取到车辆信息: {file_path}")
            return []

        # 输出文件路径
        output_file = os.path.join(
            output_dir, os.path.splitext(os.path.basename(file_path))[0] + ".csv"
        )

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        # 保存为CSV
        processor.save_to_csv(output_file)

        elapsed = time.time() - start_time
        logger.info(
            f"文件处理完成: {file_path}, 保存到: {output_file}, "
            f"记录数: {len(cars)}, 耗时: {elapsed:.2f}秒"
        )

        return cars
    except Exception as e:
        logger.error(f"处理文件失败: {file_path}, 错误: {str(e)}", exc_info=True)
        return []


def process_directory(
    input_dir: str,
    output_dir: str,
    pattern: str = "*.docx",
    config: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    处理目录中的所有文件

    Args:
        input_dir: 输入目录
        output_dir: 输出目录
        pattern: 文件匹配模式
        config: 配置信息
        verbose: 是否显示详细信息

    Returns:
        包含处理结果的字典
    """
    logger = logging.getLogger(__name__)
    logger.info(f"处理目录: {input_dir}, 匹配模式: {pattern}")

    # 收集所有文件路径
    file_pattern = os.path.join(input_dir, pattern)
    file_paths = glob.glob(file_pattern, recursive=True)

    if not file_paths:
        logger.error(f"未找到匹配的文件: {file_pattern}")
        # 返回完整的结果字典，即使发生错误
        return {
            "status": "error",
            "message": f"未找到匹配的文件: {file_pattern}",
            "total_files": 0,
            "processed_files": 0,
            "success_files": 0,
            "error_files": 0,
            "total_records": 0,
        }

    logger.info(f"找到 {len(file_paths)} 个文件")

    # 创建进度条
    progress = None
    task_id: Optional[TaskID] = None

    if verbose:
        progress = create_progress_bar(len(file_paths))
        progress.start()
        task_id = progress.tasks[0].id  # 获取第一个任务的ID

    all_cars = []
    processed_count = 0
    success_count = 0
    error_count = 0
    batch_info = BatchInfo(
        batch_number="combined",
        total_count=0,
        energy_saving_count=0,
        new_energy_count=0,
    )

    try:
        for file_path in file_paths:
            try:
                # 确保配置是字典类型
                cfg = config if config is not None else {}
                result = process_single_file(
                    file_path, output_dir, cfg, verbose=verbose
                )
                processed_count += 1

                if result:
                    all_cars.extend(result)
                    success_count += 1
                    # 将各文件的车辆信息合并到批次信息
                    for car_dict in result:
                        if car_dict.get("batch"):
                            # 构建CarInfo对象
                            car_info = CarInfo(
                                vmodel=car_dict.get("vmodel", ""),
                                category=car_dict.get("category", ""),
                                sub_type=car_dict.get("sub_type", ""),
                                batch=car_dict.get("batch", ""),
                                energytype=car_dict.get("energytype", 0),
                                company=car_dict.get("企业名称", ""),
                                brand=car_dict.get("品牌", ""),
                                table_id=car_dict.get("table_id", ""),
                                raw_text=car_dict.get("raw_text", ""),
                                extra_fields={
                                    k: v
                                    for k, v in car_dict.items()
                                    if k
                                    not in [
                                        "vmodel",
                                        "category",
                                        "sub_type",
                                        "batch",
                                        "energytype",
                                        "企业名称",
                                        "品牌",
                                        "table_id",
                                        "raw_text",
                                    ]
                                },
                            )
                            batch_info.add_car(car_info)
                else:
                    error_count += 1

                # 更新进度条
                if progress and task_id is not None:
                    progress.update(task_id, advance=1)

            except Exception as e:
                error_count += 1
                logger.error(
                    f"处理文件失败: {file_path}, 错误: {str(e)}", exc_info=True
                )

                # 更新进度条
                if progress and task_id is not None:
                    progress.update(task_id, advance=1)

        # 合并输出
        if all_cars:
            combined_output = os.path.join(output_dir, "combined_results.csv")
            try:
                # 直接使用pandas保存合并结果，避免创建空路径DocProcessor
                df = pd.DataFrame(all_cars)
                # 确保输出目录存在
                os.makedirs(os.path.dirname(combined_output), exist_ok=True)
                # 保存为CSV
                df.to_csv(combined_output, index=False, encoding="utf-8")
                logger.info(
                    f"合并结果已保存到: {combined_output}, 总记录数: {len(all_cars)}"
                )
            except Exception as e:
                logger.error(f"保存合并结果失败: {str(e)}", exc_info=True)

        # 显示统计信息
        if verbose and all_cars:
            # 计算统计数据
            stats = calculate_statistics(all_cars)
            display_statistics(
                stats["total_count"],
                stats["energy_saving_count"],
                stats["new_energy_count"],
                combined_output,
            )

    finally:
        # 关闭进度条
        if progress:
            progress.stop()

    return {
        "status": "success",
        "total_files": len(file_paths),
        "processed_files": processed_count,
        "success_files": success_count,
        "error_files": error_count,
        "total_records": len(all_cars),
        "batch_info": batch_info,
    }


def main():
    """主函数"""
    args = parse_args()

    # 设置日志
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(args.log_config)

    logger = logging.getLogger(__name__)
    logger.info("文档处理器 开始运行")
    logger.info(f"参数: {args}")

    # 加载配置
    config = {}
    if os.path.exists(args.config):
        try:
            config = load_config(args.config)
            # 初始化全局设置
            Settings(config)
            logger.info(f"加载配置文件: {args.config}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {args.config}, 错误: {str(e)}")
            logger.info("将使用默认配置")
    else:
        logger.warning(f"配置文件不存在: {args.config}, 将使用默认配置")

    # 更新配置中的命令行参数
    if not config:
        config = {}
    if "performance" not in config:
        config["performance"] = {}
    config["performance"]["chunk_size"] = args.chunk_size

    if "document" not in config:
        config["document"] = {}
    config["document"]["skip_verification"] = args.skip_verification

    start_time = time.time()

    # 处理输入
    output_dir = args.output
    if os.path.isdir(args.input):
        # 处理目录
        result = process_directory(
            args.input, output_dir, args.pattern, config, args.verbose
        )
        logger.info(f"目录处理结果: {result['status']}")
        logger.info(
            f"总文件数: {result['total_files']}, 成功: {result['success_files']}, "
            f"失败: {result['error_files']}, 总记录数: {result['total_records']}"
        )
    else:
        # 处理单个文件
        cars = process_single_file(args.input, output_dir, config, args.verbose)
        result = {
            "status": "success" if cars else "error",
            "total_files": 1,
            "processed_files": 1,
            "success_files": 1 if cars else 0,
            "error_files": 0 if cars else 1,
            "total_records": len(cars),
        }
        logger.info(
            f"文件处理结果: {result['status']}, 记录数: {result['total_records']}"
        )

    elapsed = time.time() - start_time
    logger.info(f"文档处理器 运行完成, 总耗时: {elapsed:.2f}秒")

    return 0


# 当直接运行此脚本时执行
if __name__ == "__main__":
    sys.exit(main())
