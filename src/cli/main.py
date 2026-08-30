"""Canonical Click command-line interface."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import click

from ..application import process_directory, process_single_file
from ..config.settings import ConfigurationError, load_config, setup_logging


@click.group()
def cli() -> None:
    """车辆数据文档处理工具"""


@cli.command()
@click.argument("input_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "-o",
    "--output",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("output"),
    show_default=True,
    help="输出目录",
)
@click.option("-v", "--verbose", is_flag=True, help="显示详细处理信息")
@click.option("--pattern", default="*.docx", show_default=True, help="目录递归匹配模式")
@click.option(
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="YAML/JSON 配置文件路径",
)
@click.option(
    "--log-config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="日志配置文件路径",
)
@click.option(
    "--chunk-size",
    type=click.IntRange(min=1),
    default=None,
    help="数据处理块大小（默认读取配置或使用 1000）",
)
@click.option(
    "--skip-verification",
    is_flag=True,
    default=None,
    help="跳过批次一致性验证",
)
@click.option("--classic-display", is_flag=True, default=None, help="使用传统结果显示")
def process(
    input_path: Path,
    output: Path,
    verbose: bool,
    pattern: str,
    config: Optional[Path],
    log_config: Optional[Path],
    chunk_size: Optional[int],
    skip_verification: Optional[bool],
    classic_display: Optional[bool],
) -> None:
    """处理指定的docx文件或目录下的所有docx文件"""
    # Windows legacy code pages cannot encode every literal symbol used by the
    # Rich UI. Replacing an unsupported glyph must not abort data conversion.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(errors="replace")

    setup_logging(str(log_config) if log_config else "config/logging.yaml")
    logger = logging.getLogger(__name__)

    try:
        config_data: Dict[str, Any] = (
            load_config(str(config)) if config else load_config()
        )
        performance_config = config_data.setdefault("performance", {})
        document_config = config_data.setdefault("document", {})
        output_config = config_data.setdefault("output", {})
        performance_config.setdefault("chunk_size", 1000)
        document_config.setdefault("skip_verification", False)
        output_config.setdefault("use_dashboard", True)
        if chunk_size is not None:
            performance_config["chunk_size"] = chunk_size
        if skip_verification:
            document_config["skip_verification"] = True
        if classic_display:
            output_config["use_dashboard"] = False

        if input_path.is_dir():
            result = process_directory(
                str(input_path), str(output), pattern, config_data, verbose
            )
            click.echo(
                f"处理完成 - 共处理 {result['total_files']} 个文件，"
                f"成功 {result['success_files']} 个，失败 {result['error_files']} 个，"
                f"总记录数 {result['total_records']}"
            )
            if result["status"] != "success":
                details = "; ".join(
                    f"{item['file']}: {item['error']}"
                    for item in result.get("errors", [])[:3]
                )
                message = "目录处理未全部成功"
                if details:
                    message = f"{message}: {details}"
                raise click.ClickException(message)
        else:
            records = process_single_file(
                str(input_path), str(output), config_data, verbose
            )
            if not records:
                raise click.ClickException("处理完成，但未提取到有效车辆记录")
            click.echo(f"处理成功 - 共提取 {len(records)} 条记录")
    except click.ClickException:
        raise
    except ConfigurationError as exc:
        raise click.ClickException(f"加载配置失败: {exc}") from exc
    except Exception as exc:
        logger.error("处理失败: %s", exc, exc_info=verbose)
        raise click.ClickException(f"处理失败: {exc}") from exc


def main() -> None:
    """Console-script compatible entry point."""
    cli()


if __name__ == "__main__":
    main()
