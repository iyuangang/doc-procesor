"""Tests for the shared application layer and compatibility entry points."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import doc_processor
from src import __main__ as package_main
from src.application import (
    ProcessedFile,
    process_directory,
    process_single_file,
)
from src.processor.doc_processor import ProcessingError


def test_all_entry_points_share_application_functions() -> None:
    assert doc_processor.process_single_file is process_single_file
    assert package_main.process_single_file is process_single_file
    assert doc_processor.process_directory is process_directory
    assert package_main.process_directory is process_directory


@patch("src.application.DocProcessor")
def test_process_single_file_uses_core_and_saves_csv(
    mock_processor_class: MagicMock, tmp_path: Path
) -> None:
    source = tmp_path / "sample.docx"
    source.write_bytes(b"placeholder")
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    stale_invalid_output = output_dir / "sample_invalid_records.csv"
    stale_invalid_output.write_text("stale", encoding="utf-8")
    records = [{"vmodel": "MODEL-1", "category": "新能源", "energytype": 1}]

    processor = mock_processor_class.return_value
    processor.process.return_value = records
    processor.batch_results = {"1": {"total": 1, "table_counts": {1: 1}}}
    processor.consistency_result = {"status": "match"}
    processor.invalid_records = []

    result = process_single_file(
        str(source),
        str(output_dir),
        {"output": {"use_dashboard": False}},
        display=False,
    )

    assert result == records
    processor.process.assert_called_once_with()
    processor.save_to_csv.assert_called_once_with(str(output_dir / "sample.csv"))
    assert not stale_invalid_output.exists()


@patch("src.application._render_result")
@patch("src.application.write_csv_atomic")
@patch("src.application.DocProcessor")
def test_process_single_file_exports_invalid_rows(
    mock_processor_class: MagicMock,
    mock_write_csv: MagicMock,
    mock_render: MagicMock,
    tmp_path: Path,
) -> None:
    source = tmp_path / "sample.docx"
    source.write_bytes(b"placeholder")
    output_dir = tmp_path / "output"
    invalid = {
        "source_file": "sample.docx",
        "table_id": 1,
        "row_number": 3,
        "reason": "缺少必要字段: vmodel",
    }
    processor = mock_processor_class.return_value
    processor.process.return_value = [{"vmodel": "MODEL-1"}]
    processor.invalid_records = [invalid]
    processor.batch_results = {"1": {"total": 1}}
    processor.consistency_result = {"status": "internal_mismatch"}

    process_single_file(str(source), str(output_dir))

    invalid_output = output_dir / "sample_invalid_records.csv"
    mock_write_csv.assert_called_once_with([invalid], str(invalid_output))
    assert processor.consistency_result["invalid_output_file"] == str(invalid_output)
    mock_render.assert_called_once()


def test_process_single_file_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ProcessingError, match="文件不存在"):
        process_single_file(str(tmp_path / "missing.docx"), str(tmp_path / "output"))


@patch("src.application._render_result")
@patch("src.application.write_csv_atomic")
@patch("src.application._process_file")
def test_process_directory_reports_partial_failures(
    mock_process_file: MagicMock,
    mock_write_csv: MagicMock,
    mock_render: MagicMock,
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    first = input_dir / "first.docx"
    second = input_dir / "nested" / "second.docx"
    second.parent.mkdir()
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    (input_dir / "~$locked.docx").write_bytes(b"lock")

    processor = MagicMock()
    processor.candidate_record_count = 1
    processor.invalid_record_count = 0
    processor.invalid_records = []
    record = {
        "vmodel": "MODEL-1",
        "category": "新能源",
        "sub_type": "轿车",
        "energytype": 1,
        "batch": "1",
    }
    mock_process_file.side_effect = [
        ProcessedFile(first, output_dir / "first.csv", processor, [record]),
        ProcessingError("broken document"),
    ]

    result = process_directory(str(input_dir), str(output_dir))

    assert result["status"] == "partial"
    assert result["total_files"] == 2
    assert result["success_files"] == 1
    assert result["error_files"] == 1
    assert result["total_records"] == 1
    mock_write_csv.assert_called_once()
    mock_render.assert_called_once()


@patch("src.application._render_result")
@patch("src.application.write_csv_atomic")
@patch("src.application._process_file")
def test_process_directory_exports_and_displays_invalid_record_details(
    mock_process_file: MagicMock,
    mock_write_csv: MagicMock,
    mock_render: MagicMock,
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    source = input_dir / "sample.docx"
    source.write_bytes(b"placeholder")

    invalid = {
        "source_file": "sample.docx",
        "table_id": 1,
        "row_number": 3,
        "reason": "缺少必要字段: vmodel",
    }
    processor = MagicMock()
    processor.candidate_record_count = 2
    processor.invalid_record_count = 1
    processor.invalid_records = [invalid]
    record = {
        "vmodel": "MODEL-1",
        "category": "新能源",
        "energytype": 1,
        "batch": "1",
    }
    mock_process_file.return_value = ProcessedFile(
        source, output_dir / "sample.csv", processor, [record]
    )

    result = process_directory(str(input_dir), str(output_dir))

    assert result["invalid_record_count"] == 1
    assert result["invalid_records"] == [invalid]
    assert result["invalid_output_file"] == str(
        output_dir / "combined_results_invalid_records.csv"
    )
    invalid_write = mock_write_csv.call_args_list[1]
    assert invalid_write.args == (
        [invalid],
        str(output_dir / "combined_results_invalid_records.csv"),
    )
    rendered_consistency = mock_render.call_args.args[2]
    assert rendered_consistency["invalid_records"] == [invalid]
    assert rendered_consistency["invalid_output_file"] == result["invalid_output_file"]


def test_process_directory_with_no_matches(tmp_path: Path) -> None:
    result = process_directory(str(tmp_path), str(tmp_path / "output"))
    assert result["status"] == "error"
    assert result["total_files"] == 0
