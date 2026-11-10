"""Create the synthetic sample "Drive" used by the demo (standard library only).

All content is invented for this demo. The descriptors are original wording written for this
portfolio; they are NOT the IB's descriptors and contain no student or school data.

    sample_drive/allowed/assessment/speaking_rubric_synthetic.docx      valid rubric, /30
    sample_drive/allowed/assessment/speaking_rubric_draft_errors.docx   broken on purpose
    sample_drive/allowed/assessment/speaking_guidelines_synthetic.md    format notes
    sample_drive/restricted/marks_synthetic.md                          must NOT be readable
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

DEMO_DIR = Path(__file__).resolve().parents[1]
DRIVE = DEMO_DIR / "sample_drive"

CRITERIA = [
    ("A", "LANGUAGE", [2, 4, 6, 8, 10, 12], [
        "Very limited vocabulary and basic sentences; frequent errors make the meaning hard to follow.",
        "Some suitable vocabulary and simple sentences; errors often get in the way of meaning.",
        "Generally suitable vocabulary with some attempts at longer sentences; errors sometimes obscure meaning.",
        "Varied vocabulary and a mix of simple and complex sentences; occasional errors do not block meaning.",
        "Precise, varied vocabulary including some idioms; minor errors only in complex sentences.",
        "Consistently precise and natural language; pronunciation and intonation actively support meaning.",
    ]),
    ("B1", "MESSAGE: PICTURE", [1, 2, 3, 4, 5, 6], [
        "The talk barely relates to the picture and only lists a few things in it.",
        "The talk partly relates to the picture and mostly describes it, with gaps.",
        "The talk relates to the picture, describing clear details with a little personal interpretation.",
        "The talk is relevant throughout, combining description with personal interpretation and a theme link.",
        "The talk uses obvious and less obvious details and makes clear links to the chosen theme.",
        "The talk is fully relevant, insightful about details, and makes several well-developed theme links.",
    ]),
    ("B2", "MESSAGE: DISCUSSION", [1, 2, 3, 4, 5, 6], [
        "Answers rarely address the questions and are very short.",
        "Answers sometimes address the questions and are seldom developed.",
        "Answers mostly address the questions and some are developed.",
        "Answers address the questions and are often developed with examples.",
        "Answers are consistently relevant and developed, with personal views.",
        "Answers are relevant, well developed and broad, and engage the teacher in the discussion.",
    ]),
    ("C", "INTERACTION", [1, 2, 3, 4, 5, 6], [
        "Understanding and interaction are very limited; most questions must be repeated.",
        "Understanding and interaction are limited; several questions must be rephrased.",
        "Interaction is somewhat sustained and shows general understanding of the questions.",
        "Interaction is mostly sustained and shows good understanding of the questions.",
        "Interaction is sustained, with some contributions the student starts unprompted.",
        "Interaction is active and sustained throughout, with several independent contributions.",
    ]),
]

GUIDELINES = """# Speaking assessment format (synthetic example)

The assessment has a preparation time, a presentation and a discussion.
- Preparation: 10 minutes with one picture; up to 10 bullet points of notes.
- Presentation: 1-2 minutes describing the picture and linking it to one theme.
- Discussion: 2-3 minutes of questions from the teacher about the presentation and theme.
Grading uses the speaking assessment rubric (total /30). Nothing after 5 minutes is graded.
"""

RESTRICTED = """# Marks (synthetic, restricted)

This file stands for a private document outside the folders a request may read.
Student 01: 21/30
"""


def _p(text: str, bold: bool = False) -> str:
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f"<w:p><w:r>{rpr}<w:t xml:space=\"preserve\">{escape(text)}</w:t></w:r></w:p>"


def _tc(text: str, bold: bool = False) -> str:
    return f"<w:tc><w:tcPr><w:tcW w:w=\"1500\" w:type=\"dxa\"/></w:tcPr>{_p(text, bold)}</w:tc>"


def _tbl(rows: list[list[str]]) -> str:
    body = "".join("<w:tr>" + "".join(_tc(c, j == 0) for j, c in enumerate(r)) + "</w:tr>" for r in rows)
    return ("<w:tbl><w:tblPr><w:tblStyle w:val=\"TableGrid\"/><w:tblW w:w=\"0\" w:type=\"auto\"/>"
            "</w:tblPr>" + body + "</w:tbl>")


def write_docx(path: Path, title: str, rows: list[list[str]]) -> Path:
    doc = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
           "<w:document xmlns:w=\"http://schemas.openxmlformats.org/wordprocessingml/2006/main\"><w:body>"
           + _p(title, bold=True) + _tbl(rows) + _p("")
           + "<w:sectPr><w:pgSz w:w=\"16838\" w:h=\"11906\" w:orient=\"landscape\"/></w:sectPr>"
           "</w:body></w:document>")
    types = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
             "<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">"
             "<Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/>"
             "<Default Extension=\"xml\" ContentType=\"application/xml\"/>"
             "<Override PartName=\"/word/document.xml\" ContentType=\"application/"
             "vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml\"/></Types>")
    rels = ("<?xml version=\"1.0\" encoding=\"UTF-8\" standalone=\"yes\"?>"
            "<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">"
            "<Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/"
            "relationships/officeDocument\" Target=\"word/document.xml\"/></Relationships>")
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        # A fixed timestamp keeps the file byte-for-byte reproducible.
        for name, data in (("[Content_Types].xml", types), ("_rels/.rels", rels), ("word/document.xml", doc)):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    return path


def rubric_rows(criteria) -> list[list[str]]:
    rows = []
    for key, name, marks, descriptors in criteria:
        rows.append([key] + [str(m) for m in marks])
        rows.append([name] + descriptors)
    rows.append(["Notes:"] + [""] * 6)
    return rows


def make_samples(drive: Path = DRIVE) -> dict[str, Path]:
    a = drive / "allowed" / "assessment"
    good = write_docx(a / "speaking_rubric_synthetic.docx",
                      "Speaking Assessment Rubric (synthetic example)  Total: /30", rubric_rows(CRITERIA))
    broken = [list(c) for c in CRITERIA]
    broken[1][3] = list(broken[1][3]); broken[1][3][3] = ""          # B1: a missing descriptor
    broken[3][3] = list(broken[3][3]); broken[3][3][5] = broken[3][3][4]  # C: copy-paste duplicate
    bad = write_docx(a / "speaking_rubric_draft_errors.docx",
                     "Speaking Assessment Rubric DRAFT (synthetic)  Total: /40", rubric_rows(broken))
    guide = a / "speaking_guidelines_synthetic.md"
    guide.write_text(GUIDELINES, encoding="utf-8")
    restricted = drive / "restricted" / "marks_synthetic.md"
    restricted.parent.mkdir(parents=True, exist_ok=True)
    restricted.write_text(RESTRICTED, encoding="utf-8")
    return {"good": good, "broken": bad, "guidelines": guide, "restricted": restricted}


if __name__ == "__main__":
    for k, p in make_samples().items():
        print(f"{k:11s} {p.relative_to(DEMO_DIR)}")
