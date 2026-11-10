"""Authorized document retrieval with citations (a local stand-in for Google Drive).

In localEd, documents come from Google Drive, and only folders on an allow-list may be read.
Here a local folder plays the Drive: `allowed_roots` are the folders a request may read, and
anything else is refused. The search is a simple keyword score over each document's text,
which is enough to show the contract: every result names its file and where in it the match is.
(localEd itself uses hybrid vector + keyword search over an index; that needs a local
embedding model and is not part of this demo.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rubric_pipeline.docx_tables import DocxError, read_docx


class AccessDenied(PermissionError):
    pass


@dataclass
class Hit:
    path: Path
    score: int
    where: str  # citation: which paragraph/table matched first
    snippet: str


def check_access(path: Path, allowed_roots: list[Path]) -> Path:
    """Resolve `path` and refuse anything outside the allow-list (also blocks ../ tricks)."""
    real = path.resolve()
    for root in allowed_roots:
        if real == root.resolve() or root.resolve() in real.parents:
            return real
    raise AccessDenied(f"{path.name} is outside the folders this request may read.")


def _terms(text: str) -> list[str]:
    stop = {"the", "a", "an", "and", "or", "for", "of", "to", "in", "on", "please", "me",
            "my", "our", "this", "that", "with", "from", "it", "is", "use", "get"}
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2 and t not in stop]


def _units(path: Path) -> list[tuple[str, str]]:
    """(citation, text) pieces of a document."""
    if path.suffix.lower() == ".docx":
        content = read_docx(path)
        units = [(f"paragraph {i}", p) for i, p in enumerate(content.paragraphs, start=1)]
        for t in content.tables:
            for row in t.rows:
                units.append((f"table {t.index}, row {row[0].row}", " | ".join(c.text for c in row)))
        return units
    if path.suffix.lower() in (".md", ".txt"):
        lines = path.read_text(encoding="utf-8").splitlines()
        return [(f"line {i}", l) for i, l in enumerate(lines, start=1) if l.strip()]
    return []


def search(request: str, allowed_roots: list[Path], limit: int = 3) -> list[Hit]:
    terms = _terms(request)
    hits = []
    for root in allowed_roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            check_access(path, allowed_roots)
            try:
                units = _units(path)
            except DocxError:
                continue
            name_terms = set(_terms(path.stem.replace("_", " ")))
            matched, first = set(), None
            for where, text in units:
                found = {t for t in terms if t in text.lower()}
                if found and first is None:
                    first = (where, text)
                matched |= found
            # Distinct request terms found in the text, plus a bonus for terms in the file name
            # (teachers usually name files after what they are).
            score = 2 * len(matched) + 5 * len(name_terms & set(terms))
            if score and first:
                hits.append(Hit(path, score, first[0], " ".join(first[1].split())[:120]))
    return sorted(hits, key=lambda h: -h.score)[:limit]
