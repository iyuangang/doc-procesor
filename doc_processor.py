#!/usr/bin/env python3
"""Backward-compatible wrapper for legacy script and console entry points."""

from src.application import process_directory, process_single_file
from src.cli.main import cli
from src.config.settings import ConfigurationError, load_config, setup_logging


def main() -> None:
    """Run the canonical command-line interface."""
    cli()


if __name__ == "__main__":
    main()
