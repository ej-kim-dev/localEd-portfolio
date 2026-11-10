"""Turn a rubric table into structured criteria, each value traced to the cell it came from.

Recognised layout (the one our school's speaking rubric uses):

    | A        | 2           | 4           | ... | 12          |   <- marks row: key + band marks
    | LANGUAGE | descriptor  | descriptor  | ... | descriptor  |   <- name row: name + descriptors
    | B1       | 1           | 2           | ... | 6           |
    | MESSAGE… | …                                              |

A document title such as "Speaking Assessment Rubric  Total: /30" gives the declared total.
Anything that doesn't fit the layout is reported as a warning instead of being guessed, so the
validation step and the teacher can see it.

This step is deterministic (no language model): the same file always gives the same result.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from rubric_pipeline.docx_tables import Cell, DocxContent

_KEY = re.compile(r"^[A-Z][0-9]?$")
_TOTAL = re.compile(r"(?:total|총점)\s*:?\s*/\s*(\d+)", re.IGNORECASE)


@dataclass
class Band:
    marks: int
    descriptor: str
    marks_ref: str  # where the mark number came from
    descriptor_ref: str  # where the descriptor came from


@dataclass
class Criterion:
    key: str
    name: str
    bands: list[Band]
    name_ref: str

    @property
    def max_marks(self) -> int:
        return max((b.marks for b in self.bands), default=0)


@dataclass
class ExtractedRubric:
    source: str
    title: str
    declared_total: int | None
    declared_total_ref: str | None
    criteria: list[Criterion] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return sum(c.max_marks for c in self.criteria)

    @classmethod
    def from_dict(cls, d: dict) -> "ExtractedRubric":
        crit = [Criterion(c["key"], c["name"], [Band(**b) for b in c["bands"]], c["name_ref"])
                for c in d["criteria"]]
        return cls(d["source"], d["title"], d["declared_total"], d["declared_total_ref"], crit,
                   list(d.get("warnings", [])))

    def to_dict(self) -> dict:
        d = asdict(self)
        for c, src in zip(d["criteria"], self.criteria):
            c["max_marks"] = src.max_marks
        d["total"] = self.total
        return d


def _is_marks_row(row: list[Cell]) -> bool:
    return (len(row) >= 2 and bool(_KEY.match(row[0].text.strip()))
            and all(re.fullmatch(r"\d+", c.text.strip() or "x") for c in row[1:]))


def _find_total(content: DocxContent) -> tuple[int | None, str | None]:
    for i, p in enumerate(content.paragraphs, start=1):
        m = _TOTAL.search(p)
        if m:
            return int(m.group(1)), f"paragraph {i}"
    for t in content.tables:
        for row in t.rows:
            for c in row:
                m = _TOTAL.search(c.text)
                if m:
                    return int(m.group(1)), c.ref
    return None, None


def extract_rubric(content: DocxContent) -> ExtractedRubric:
    total, total_ref = _find_total(content)
    title = next((p for p in content.paragraphs if p.strip()), content.source)
    title = _TOTAL.sub("", title).strip(" -:") or content.source
    result = ExtractedRubric(content.source, title, total, total_ref, warnings=list(content.warnings))

    for table in content.tables:
        rows = table.rows
        i = 0
        while i < len(rows):
            row = rows[i]
            if not _is_marks_row(row):  # e.g. a "Notes:" row; descriptor rows are read below
                i += 1
                continue
            key_cell, mark_cells = row[0], row[1:]
            if i + 1 >= len(rows):
                result.warnings.append(f"criterion {key_cell.text} ({key_cell.ref}) has no descriptor row")
                i += 1
                continue
            name_row = rows[i + 1]
            by_col = {c.col: c for c in name_row}
            bands = []
            for mc in mark_cells:
                dc = by_col.get(mc.col)
                if dc is None:
                    result.warnings.append(
                        f"criterion {key_cell.text}: no descriptor under the {mc.text}-mark band ({mc.ref})")
                    bands.append(Band(int(mc.text), "", mc.ref, ""))
                else:
                    bands.append(Band(int(mc.text), " ".join(dc.text.split()), mc.ref, dc.ref))
            name_cell = name_row[0]
            result.criteria.append(Criterion(key_cell.text.strip(), " ".join(name_cell.text.split()).title(),
                                             bands, name_cell.ref))
            i += 2
    if not result.criteria:
        result.warnings.append("no criteria found: the table layout was not recognised")
    return result
