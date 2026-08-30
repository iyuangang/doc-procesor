"""Compatibility entry point for ``python -m src``.

All command-line forms intentionally use the same Click command tree.
Application helpers remain re-exported for existing Python callers.
"""

from .application import process_directory, process_single_file
from .cli.main import cli


def main() -> None:
    """Run the canonical command-line interface."""
    cli()


if __name__ == "__main__":
    main()
