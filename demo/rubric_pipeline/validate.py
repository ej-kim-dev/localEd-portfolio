"""Check an extracted rubric before anyone may grade with it.

Every check is a plain rule a teacher can read. A rubric with any ERROR cannot be approved;
WARNINGs are shown to the teacher, who decides.
"""

from __future__ import annotations

from dataclasses import dataclass

from rubric_pipeline.extract import ExtractedRubric


@dataclass
class Finding:
    level: str  # "ERROR" or "WARNING"
    message: str


def validate(r: ExtractedRubric) -> list[Finding]:
    out: list[Finding] = []
    err = lambda m: out.append(Finding("ERROR", m))  # noqa: E731
    warn = lambda m: out.append(Finding("WARNING", m))  # noqa: E731

    if not r.criteria:
        err("No criteria were found.")
        return out
    keys = [c.key for c in r.criteria]
    for k in sorted({k for k in keys if keys.count(k) > 1}):
        err(f"Criterion key {k} appears more than once.")
    for c in r.criteria:
        if not c.name:
            err(f"Criterion {c.key} has no name ({c.name_ref}).")
        marks = [b.marks for b in c.bands]
        if len(marks) < 2:
            err(f"Criterion {c.key} has fewer than two mark bands.")
        if marks != sorted(set(marks)):
            err(f"Criterion {c.key}: band marks must strictly increase, found {marks}.")
        for b in c.bands:
            if not b.descriptor:
                err(f"Criterion {c.key}: the {b.marks}-mark band has no descriptor ({b.marks_ref}).")
            elif len(b.descriptor.split()) < 5:
                warn(f"Criterion {c.key}: the {b.marks}-mark descriptor is very short ({b.descriptor_ref}).")
        texts = [b.descriptor for b in c.bands if b.descriptor]
        if len(texts) != len(set(texts)):
            err(f"Criterion {c.key}: two bands have identical descriptors (copy-paste error?).")
    if r.declared_total is None:
        warn("The document does not state a total; it could not be cross-checked.")
    elif r.declared_total != r.total:
        err(f"The document says the total is /{r.declared_total} ({r.declared_total_ref}), "
            f"but the criteria add up to /{r.total}.")
    for w in r.warnings:
        warn(w)
    return out


def has_errors(findings: list[Finding]) -> bool:
    return any(f.level == "ERROR" for f in findings)
