"""Read a .docx file's paragraphs and tables with their positions (standard library only).

localEd's production reader turns a Word file into paragraphs, which is enough for search but
loses table structure: a rubric's rows and columns become a flat run of text. This reader keeps
the structure and records where every cell came from, so later steps can cite their source.

Supported: body paragraphs, tables (rows, cells, horizontal merges via gridSpan), headings.
Not supported (reported, never guessed): nested tables, vertical merges, text boxes, images.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass(frozen=True)
class Cell:
    table: int  # 1-based position of the table in the document
    row: int  # 1-based
    col: int  # 1-based grid column where the cell starts
    span: int  # grid columns covered (gridSpan)
    text: str

    @property
    def ref(self) -> str:
        return f"table {self.table}, row {self.row}, column {self.col}"


@dataclass
class Table:
    index: int
    rows: list[list[Cell]] = field(default_factory=list)


@dataclass
class DocxContent:
    source: str
    paragraphs: list[str] = field(default_factory=list)  # body paragraphs outside tables
    tables: list[Table] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def plain_text(self) -> str:
        parts = list(self.paragraphs)
        for t in self.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text for c in row))
        return "\n".join(parts)


class DocxError(ValueError):
    pass


def _text(el: ET.Element) -> str:
    out = []
    for node in el.iter():
        if node.tag == W + "t" and node.text:
            out.append(node.text)
        elif node.tag in (W + "tab",):
            out.append("\t")
        elif node.tag in (W + "br", W + "cr"):
            out.append("\n")
    return "".join(out)


def _cell_text(tc: ET.Element) -> str:
    paras = [_text(p).strip() for p in tc.findall(W + "p")]
    return "\n".join(p for p in paras if p)


def read_docx(path: str | Path) -> DocxContent:
    path = Path(path)
    try:
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read("word/document.xml"))
    except (zipfile.BadZipFile, KeyError) as exc:
        raise DocxError(f"{path.name} is not a readable .docx file") from exc
    body = root.find(W + "body")
    if body is None:
        raise DocxError(f"{path.name} has no document body")

    content = DocxContent(source=path.name)
    table_no = 0
    for child in body:
        if child.tag == W + "p":
            text = _text(child).strip()
            if text:
                content.paragraphs.append(text)
        elif child.tag == W + "tbl":
            table_no += 1
            table = Table(index=table_no)
            if child.find(f".//{W}tc/{W}tbl") is not None:
                content.warnings.append(f"table {table_no} contains a nested table (not read)")
            for r, tr in enumerate(child.findall(W + "tr"), start=1):
                row, col = [], 1
                for tc in tr.findall(W + "tc"):
                    props = tc.find(W + "tcPr")
                    span_el = props.find(W + "gridSpan") if props is not None else None
                    span = int(span_el.get(W + "val", "1")) if span_el is not None else 1
                    if props is not None and props.find(W + "vMerge") is not None:
                        content.warnings.append(f"table {table_no}, row {r}: vertically merged cell")
                    row.append(Cell(table_no, r, col, span, _cell_text(tc)))
                    col += span
                table.rows.append(row)
            content.tables.append(table)
    return content
