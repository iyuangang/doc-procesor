"""Low-memory iterators for the main OOXML Word document part."""

from __future__ import annotations

from typing import Any, Iterator, List, Tuple
from zipfile import BadZipFile, ZipFile

from lxml import etree

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
PARAGRAPH_TAG = f"{{{WORD_NAMESPACE}}}p"
TABLE_TAG = f"{{{WORD_NAMESPACE}}}tbl"
ROW_TAG = f"{{{WORD_NAMESPACE}}}tr"
CELL_TAG = f"{{{WORD_NAMESPACE}}}tc"
TEXT_TAG = f"{{{WORD_NAMESPACE}}}t"


class StreamingDocumentError(Exception):
    """Raised when the OOXML document body cannot be streamed."""


def _clear_element(element: Any) -> None:
    parent = element.getparent()
    element.clear()
    if parent is not None:
        while element.getprevious() is not None:
            del parent[0]


def paragraph_text(element: Any) -> str:
    """Extract visible text nodes from an OOXML paragraph."""
    return "".join(node.text or "" for node in element.iter(TEXT_TAG)).strip()


def iter_document_blocks(doc_path: str) -> Iterator[Tuple[str, Any]]:
    """Yield paragraphs and lazy table-row iterators in body order.

    Every completed table row is cleared before parsing continues. A caller
    therefore retains record values, but never the full WordprocessingML table
    tree.
    """
    try:
        with ZipFile(doc_path) as archive:
            with archive.open("word/document.xml") as document_xml:
                context = iter(
                    etree.iterparse(
                        document_xml,
                        events=("start", "end"),
                        tag=(PARAGRAPH_TAG, TABLE_TAG, ROW_TAG),
                        huge_tree=True,
                        resolve_entities=False,
                    )
                )

                def table_rows() -> Iterator[List[str]]:
                    table_depth = 1
                    for event, element in context:
                        if element.tag == TABLE_TAG:
                            if event == "start":
                                table_depth += 1
                            else:
                                table_depth -= 1
                                if table_depth == 0:
                                    _clear_element(element)
                                    return
                        elif (
                            event == "end"
                            and element.tag == ROW_TAG
                            and table_depth == 1
                        ):
                            cells: List[str] = []
                            for cell in element.iter(CELL_TAG):
                                text = "".join(
                                    node.text or "" for node in cell.iter(TEXT_TAG)
                                )
                                cells.append(text.strip())
                            yield cells
                            _clear_element(element)

                for event, element in context:
                    if event == "end" and element.tag == PARAGRAPH_TAG:
                        yield "paragraph", paragraph_text(element)
                        _clear_element(element)
                    elif event == "start" and element.tag == TABLE_TAG:
                        yield "table", table_rows()
                del context
    except (BadZipFile, KeyError, OSError, etree.XMLSyntaxError) as exc:
        raise StreamingDocumentError(f"无法流式读取文档 {doc_path}: {exc}") from exc
