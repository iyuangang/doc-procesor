"""Application-level orchestration shared by every command-line entry point."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .batch.validator import (
    calculate_statistics,
    verify_all_batches,
    verify_batch_consistency,
)
from .models.car_info import BatchInfo, CarInfo
from .processor.doc_processor import DocProcessor, ProcessingError
from .ui.console import (
    display_batch_verification,
    display_consistency_result,
    display_statistics,
    display_summary_dashboard,
)
from .utils.csv_output import write_csv_atomic

logger = logging.getLogger(__name__)


@dataclass
class ProcessedFile:
    """A successfully opened document and its processing outcome."""

    path: Path
    output_file: Path
    processor: DocProcessor
    records: List[Dict[str, Any]]


def _render_result(
    records: List[Dict[str, Any]],
    batch_results: Dict[str, Any],
    consistency_result: Dict[str, Any],
    output_file: Path,
    config: Dict[str, Any],
    verbose: bool,
) -> None:
    output_config = config.get("output", {})
    if output_config.get("use_dashboard", True):
        display_summary_dashboard(
            records, batch_results, consistency_result, str(output_file)
        )
        return

    if batch_results:
        display_batch_verification(batch_results)
    display_consistency_result(consistency_result)

    if verbose:
        stats = calculate_statistics(records)
        display_statistics(
            stats["total_count"],
            stats["energy_saving_count"],
            stats["new_energy_count"],
            str(output_file),
        )


def _process_file(
    file_path: str,
    output_dir: str,
    config: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
    display: bool = True,
) -> ProcessedFile:
    source = Path(file_path)
    if not source.is_file():
        raise ProcessingError(f"文件不存在或不是普通文件: {source}")
    if source.suffix.lower() != ".docx":
        raise ProcessingError(f"不支持的文件格式: {source.suffix or '无扩展名'}")

    effective_config = config or {}
    destination_dir = Path(output_dir)
    destination = destination_dir / f"{source.stem}.csv"
    logger.info("处理文件: %s", source)

    processor = DocProcessor(str(source), verbose=verbose, config=effective_config)
    records = processor.process()
    if records:
        processor.save_to_csv(str(destination))
        if display:
            _render_result(
                records,
                processor.batch_results,
                processor.consistency_result,
                destination,
                effective_config,
                verbose,
            )
    else:
        logger.warning("未提取到有效车辆记录: %s", source)

    return ProcessedFile(source, destination, processor, records)


def process_single_file(
    file_path: str,
    output_dir: str,
    config: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
    *,
    display: bool = True,
) -> List[Dict[str, Any]]:
    """Process one Word document and return its valid vehicle records.

    Document and processing failures are deliberately allowed to propagate so
    callers can distinguish them from a valid document containing no records.
    """
    return _process_file(file_path, output_dir, config, verbose, display).records


def _find_documents(input_dir: Path, pattern: str) -> List[Path]:
    if any(separator in pattern for separator in ("/", "\\")):
        candidates = input_dir.glob(pattern)
    else:
        candidates = input_dir.rglob(pattern)
    return sorted(
        path for path in candidates if path.is_file() and not path.name.startswith("~$")
    )


def process_directory(
    input_dir: str,
    output_dir: str,
    pattern: str = "*.docx",
    config: Optional[Dict[str, Any]] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    """Process matching documents recursively and write individual/combined CSVs."""
    source_dir = Path(input_dir)
    if not source_dir.is_dir():
        raise ProcessingError(f"输入目录不存在: {source_dir}")

    file_paths = _find_documents(source_dir, pattern)
    if not file_paths:
        return {
            "status": "error",
            "message": f"未找到匹配的文件: {source_dir / pattern}",
            "total_files": 0,
            "processed_files": 0,
            "success_files": 0,
            "error_files": 0,
            "total_records": 0,
            "errors": [],
        }

    effective_config = config or {}
    all_records: List[Dict[str, Any]] = []
    successful: List[ProcessedFile] = []
    errors: List[Dict[str, str]] = []

    for path in file_paths:
        try:
            result = _process_file(
                str(path), output_dir, effective_config, verbose, display=False
            )
            if not result.records:
                raise ProcessingError("未提取到有效车辆记录")
            successful.append(result)
            all_records.extend(result.records)
        except Exception as exc:
            logger.error("处理文件失败: %s: %s", path, exc, exc_info=verbose)
            errors.append({"file": str(path), "error": str(exc)})

    combined_output = Path(output_dir) / "combined_results.csv"
    if all_records:
        write_csv_atomic(all_records, str(combined_output))

        batch_results = verify_all_batches(all_records)
        total_candidates = sum(
            item.processor.candidate_record_count for item in successful
        )
        total_invalid = sum(item.processor.invalid_record_count for item in successful)
        batch_number = (
            next(iter(batch_results)) if len(batch_results) == 1 else "combined"
        )

        if effective_config.get("document", {}).get("skip_verification", False):
            consistency_result: Dict[str, Any] = {
                "status": "skipped",
                "message": "已按配置跳过批次一致性验证",
                "batch": batch_number,
                "actual_count": len(all_records),
                "candidate_count": total_candidates,
                "invalid_count": total_invalid,
            }
        else:
            consistency_result = verify_batch_consistency(
                all_records,
                batch_number,
                candidate_count=total_candidates,
                invalid_count=total_invalid,
            )

        if len(batch_results) > 1:
            consistency_result["multiple_batches"] = True
            consistency_result["batch_count"] = len(batch_results)

        _render_result(
            all_records,
            batch_results,
            consistency_result,
            combined_output,
            effective_config,
            verbose,
        )

    batch_info = BatchInfo(batch_number="combined")
    for record in all_records:
        batch_info.add_car(CarInfo.from_dict(record.copy()))

    success_count = len(successful)
    if success_count == len(file_paths):
        status = "success"
    elif success_count:
        status = "partial"
    else:
        status = "error"

    return {
        "status": status,
        "total_files": len(file_paths),
        "processed_files": len(file_paths),
        "success_files": success_count,
        "error_files": len(errors),
        "total_records": len(all_records),
        "batch_info": batch_info,
        "output_file": str(combined_output) if all_records else None,
        "errors": errors,
    }
