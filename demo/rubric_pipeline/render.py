"""Outputs: structured JSON, a rubric file in localEd's Markdown format, and a review page.

The review page is what the teacher checks before approving. It shows every descriptor next
to its source cell and the validation findings, and is clearly labelled as pending approval.
"""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from rubric_pipeline.extract import ExtractedRubric
from rubric_pipeline.validate import Finding


def write_json(r: ExtractedRubric, path: Path) -> Path:
    path.write_text(json.dumps(r.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def to_localed_markdown(r: ExtractedRubric) -> str:
    """The rubric file format localEd's grader loads ("## Criterion X: Name (max N)")."""
    lines = ["---", f"title: {r.title}", f"total_max: {r.total}",
             f"notes: Extracted from {r.source}; every descriptor lists its source cell.", "---", ""]
    for c in r.criteria:
        lines.append(f"## Criterion {c.key}: {c.name} (max {c.max_marks})")
        lines.append("")
        for b in c.bands:
            lines.append(f"- **{b.marks} marks**: {b.descriptor} _(source: {b.descriptor_ref})_")
        lines.append("")
    return "\n".join(lines)


def to_review_html(r: ExtractedRubric, findings: list[Finding], status: str) -> str:
    rows = []
    for c in r.criteria:
        for i, b in enumerate(c.bands):
            head = (f"<td rowspan='{len(c.bands)}'><b>{escape(c.key)}</b><br>{escape(c.name)}"
                    f"<br><small>max {c.max_marks}</small></td>") if i == 0 else ""
            rows.append(f"<tr>{head}<td>{b.marks}</td><td>{escape(b.descriptor) or '<i>missing</i>'}</td>"
                        f"<td><small>{escape(b.descriptor_ref)}</small></td></tr>")
    issues = "".join(f"<li><b>{f.level}</b>: {escape(f.message)}</li>" for f in findings) or "<li>No issues found.</li>"
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Rubric review</title>
<style>body{{font-family:Arial,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem}}
.banner{{background:#fff3cd;color:#664d03;padding:.6rem;font-weight:bold}}
table{{border-collapse:collapse}}td,th{{border:1px solid #bbb;padding:.3rem .5rem;vertical-align:top}}</style>
</head><body><p class="banner">STATUS: {escape(status)}</p>
<h1>{escape(r.title)}</h1>
<p>Source: {escape(r.source)} · Criteria: {len(r.criteria)} · Total: /{r.total}
(document states /{r.declared_total if r.declared_total is not None else '?'})</p>
<h2>Validation</h2><ul>{issues}</ul>
<h2>Criteria</h2><table><tr><th>Criterion</th><th>Marks</th><th>Descriptor</th><th>Source</th></tr>
{''.join(rows)}</table></body></html>
"""
