"""Tests for canonical CLI behavior and exit codes."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml
from click.testing import CliRunner

from src.cli.main import cli


def test_cli_command_structure() -> None:
    assert "process" in cli.commands
    names = [parameter.name for parameter in cli.commands["process"].params]
    assert names == [
        "input_path",
        "output",
        "verbose",
        "pattern",
        "config",
        "log_config",
        "chunk_size",
        "skip_verification",
        "classic_display",
    ]


@patch("src.cli.main.setup_logging")
@patch("src.cli.main.process_single_file")
def test_single_file_success(
    mock_process: MagicMock, mock_logging: MagicMock, tmp_path: Path
) -> None:
    source = tmp_path / "sample.docx"
    source.write_bytes(b"placeholder")
    mock_process.return_value = [{"vmodel": "MODEL-1"}]

    result = CliRunner().invoke(cli, ["process", str(source)])

    assert result.exit_code == 0
    assert "共提取 1 条记录" in result.output
    config = mock_process.call_args.args[2]
    assert config["document"]["skip_verification"] is False


@patch("src.cli.main.setup_logging")
@patch("src.cli.main.process_single_file", return_value=[])
def test_empty_result_has_nonzero_exit(
    mock_process: MagicMock, mock_logging: MagicMock, tmp_path: Path
) -> None:
    source = tmp_path / "sample.docx"
    source.write_bytes(b"placeholder")
    result = CliRunner().invoke(cli, ["process", str(source)])
    assert result.exit_code != 0
    assert "未提取到有效车辆记录" in result.output


@patch("src.cli.main.setup_logging")
@patch("src.cli.main.process_directory")
def test_partial_directory_has_nonzero_exit(
    mock_process: MagicMock, mock_logging: MagicMock, tmp_path: Path
) -> None:
    mock_process.return_value = {
        "status": "partial",
        "total_files": 2,
        "success_files": 1,
        "error_files": 1,
        "total_records": 1,
        "errors": [{"file": "bad.docx", "error": "broken"}],
    }
    result = CliRunner().invoke(cli, ["process", str(tmp_path)])
    assert result.exit_code != 0
    assert "目录处理未全部成功" in result.output


@patch("src.cli.main.setup_logging")
@patch("src.cli.main.process_single_file", return_value=[{"vmodel": "MODEL-1"}])
def test_cli_overrides_are_forwarded(
    mock_process: MagicMock, mock_logging: MagicMock, tmp_path: Path
) -> None:
    source = tmp_path / "sample.docx"
    source.write_bytes(b"placeholder")
    result = CliRunner().invoke(
        cli,
        [
            "process",
            str(source),
            "--chunk-size",
            "50",
            "--skip-verification",
            "--classic-display",
        ],
    )
    assert result.exit_code == 0
    config = mock_process.call_args.args[2]
    assert config["performance"]["chunk_size"] == 50
    assert config["document"]["skip_verification"] is True
    assert config["output"]["use_dashboard"] is False


@patch("src.cli.main.setup_logging")
@patch("src.cli.main.process_single_file", return_value=[{"vmodel": "MODEL-1"}])
def test_config_values_are_preserved_without_cli_overrides(
    mock_process: MagicMock, mock_logging: MagicMock, tmp_path: Path
) -> None:
    source = tmp_path / "sample.docx"
    source.write_bytes(b"placeholder")
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.safe_dump(
            {
                "performance": {"chunk_size": 42},
                "document": {"skip_verification": True},
                "output": {"use_dashboard": False},
            }
        ),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["process", str(source), "--config", str(config_file)]
    )

    assert result.exit_code == 0
    config = mock_process.call_args.args[2]
    assert config["performance"]["chunk_size"] == 42
    assert config["document"]["skip_verification"] is True
    assert config["output"]["use_dashboard"] is False
