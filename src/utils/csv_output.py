"""CSV output helpers.

The processor already keeps records in memory, so collecting the complete field
set is inexpensive and prevents columns that appear late in a document from
being silently dropped. Files are written beside the destination and then
atomically replaced to avoid leaving partial output behind.
"""

from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


BASE_COLUMNS: Sequence[str] = (
    "batch",
    "energytype",
    "vmodel",
    "category",
    "sub_type",
    "序号",
    "企业名称",
    "品牌",
    "table_id",
    "raw_text",
)


def collect_fieldnames(records: Iterable[Dict[str, Any]]) -> List[str]:
    """Return deterministic field names without losing late-occurring fields."""
    discovered: List[str] = []
    seen = set()
    for record in records:
        for field in record:
            if field not in seen:
                seen.add(field)
                discovered.append(field)

    return [field for field in BASE_COLUMNS if field in seen] + [
        field for field in discovered if field not in BASE_COLUMNS
    ]


def write_csv_atomic(records: List[Dict[str, Any]], output_file: str) -> bool:
    """Write records as UTF-8 BOM CSV and atomically replace the destination.

    Returns ``False`` for an empty record list and leaves any existing output
    untouched.
    """
    if not records:
        return False

    destination = Path(output_file)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = collect_fieldnames(records)
    temporary_path: Optional[Path] = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8-sig",
            newline="",
            dir=str(destination.parent),
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            writer = csv.DictWriter(
                temporary,
                fieldnames=fieldnames,
                extrasaction="ignore",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(records)
            temporary.flush()
            os.fsync(temporary.fileno())

        os.replace(temporary_path, destination)
        temporary_path = None
        return True
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
