"""Synthetic benchmark cases for rubric extraction.

Each case is built from a small spec, and the expected result is derived from the same spec
(where each value was placed), never from the extractor's output. Cases cover layout
variations seen in real school documents, planted errors the validator must catch, and
layouts the extractor is not designed for (it must report them, not guess).

All text is synthetic. Korean descriptors were written for this benchmark.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

from rubric_pipeline.samples import CRITERIA

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

KOREAN = [
    ("A", "언어", [2, 4, 6, 8, 10, 12], [
        "어휘가 매우 제한적이고 기본 문장만 사용하며 오류가 잦아 의미 전달이 어렵다.",
        "적절한 어휘를 일부 사용하나 오류가 자주 의미 전달을 방해한다.",
        "대체로 적절한 어휘를 사용하며 긴 문장을 시도하나 가끔 의미가 흐려진다.",
        "다양한 어휘와 복문을 사용하며 가끔의 오류가 의미 전달을 막지 않는다.",
        "정확하고 다양한 어휘를 사용하며 복문에서만 사소한 오류가 있다.",
        "언어가 정확하고 자연스러우며 발음과 억양이 의미 전달을 돕는다.",
    ]),
    ("B1", "메시지: 사진", [1, 2, 3, 4, 5, 6], [
        "발표가 사진과 거의 관련이 없고 몇 가지를 나열하는 데 그친다.",
        "발표가 사진과 부분적으로 관련되며 주로 묘사에 머문다.",
        "사진의 분명한 세부 사항을 묘사하고 약간의 개인적 해석을 더한다.",
        "묘사와 개인적 해석을 함께 제시하고 주제와 연결한다.",
        "드러난 세부와 숨은 세부를 활용하여 주제와 분명하게 연결한다.",
        "통찰력 있게 세부를 다루며 주제와 여러 번 깊이 있게 연결한다.",
    ]),
    ("B2", "메시지: 토론", [1, 2, 3, 4, 5, 6], [
        "질문에 거의 답하지 못하고 답이 매우 짧다.",
        "질문에 가끔 답하나 내용이 거의 발전되지 않는다.",
        "대체로 질문에 답하고 일부 답을 발전시킨다.",
        "질문에 답하며 예시로 자주 내용을 발전시킨다.",
        "일관되게 관련 있는 답을 하며 개인적 견해를 더한다.",
        "폭넓고 깊이 있는 답으로 교사와의 토론을 이끈다.",
    ]),
    ("C", "상호작용", [1, 2, 3, 4, 5, 6], [
        "이해와 상호작용이 매우 제한적이며 대부분의 질문을 반복해야 한다.",
        "이해와 상호작용이 제한적이며 여러 질문을 바꾸어 말해야 한다.",
        "상호작용이 어느 정도 유지되며 질문을 대체로 이해한다.",
        "상호작용이 대부분 유지되며 질문을 잘 이해한다.",
        "상호작용이 유지되며 학생이 스스로 일부 내용을 덧붙인다.",
        "상호작용이 활발히 유지되며 학생이 여러 번 스스로 기여한다.",
    ]),
]

# A cell is a string, a list of paragraphs, or (text, gridspan).
CellSpec = "str | list[str] | tuple[str, int]"


@dataclass
class Case:
    name: str
    description: str
    title: str
    tables: list[list[list]]  # tables -> rows -> cells
    expect_extract: bool = True  # False: the layout is out of scope and must be reported
    expected: dict | None = None  # criteria with values and source refs
    expected_errors: list[str] = field(default_factory=list)  # substrings the validator must report


def _p(text: str) -> str:
    return f'<w:p><w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def _cell(spec) -> str:
    span = 1
    if isinstance(spec, tuple):
        spec, span = spec
    paras = spec if isinstance(spec, list) else [spec]
    props = f'<w:tcPr><w:gridSpan w:val="{span}"/></w:tcPr>' if span > 1 else "<w:tcPr/>"
    return "<w:tc>" + props + "".join(_p(t) for t in paras) + "</w:tc>"


def build_docx(case: Case, path: Path) -> Path:
    body = _p(case.title)
    for table in case.tables:
        body += "<w:tbl><w:tblPr/>" + "".join(
            "<w:tr>" + "".join(_cell(c) for c in row) + "</w:tr>" for row in table) + "</w:tbl>" + _p("")
    doc = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document xmlns:w="{W_NS}">'
           f"<w:body>{body}<w:sectPr/></w:body></w:document>")
    types = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" '
             'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/></Relationships>')
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in (("[Content_Types].xml", types), ("_rels/.rels", rels), ("word/document.xml", doc)):
            z.writestr(zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)), data)
    return path


def _rubric_table(criteria, *, blank_between=False, header=None, split_cells=False, descending=False):
    """Rows for a rubric table plus the expected structure (with the cell refs we used)."""
    rows, expected = [], []
    if header:
        rows.append([(header, len(criteria[0][2]) + 1)])
    for key, name, marks, descs in criteria:
        pairs = list(zip(marks, descs))
        if descending:
            pairs = pairs[::-1]
        marks_row = len(rows) + 1
        rows.append([key] + [str(m) for m, _ in pairs])
        name_row = len(rows) + 1
        cells = []
        for _, d in pairs:
            if split_cells and len(d.split(". ")) == 1 and "; " in d:
                first, rest = d.split("; ", 1)
                cells.append([first + ";", rest])
            else:
                cells.append(d)
        rows.append([name] + cells)
        bands = [{"marks": m, "descriptor": d,
                  "marks_ref": f"row {marks_row}, column {j}", "descriptor_ref": f"row {name_row}, column {j}"}
                 for j, (m, d) in enumerate(pairs, start=2)]
        expected.append({"key": key, "name": name, "max_marks": max(marks), "bands": bands,
                         "name_ref": f"row {name_row}, column 1"})
        if blank_between:
            rows.append([""] * (len(pairs) + 1))
    return rows, expected


def _with_table(expected, table_no):
    for c in expected:
        c["name_ref"] = f"table {table_no}, {c['name_ref']}"
        for b in c["bands"]:
            b["marks_ref"] = f"table {table_no}, {b['marks_ref']}"
            b["descriptor_ref"] = f"table {table_no}, {b['descriptor_ref']}"
    return {"criteria": expected}


def all_cases() -> list[Case]:
    cases = []

    def add(name, desc, criteria, title="Speaking Rubric Total: /30", stated_total=30, tables_before=(),
            errors=(), **kw):
        rows, exp = _rubric_table(criteria, **kw)
        tables = list(tables_before) + [rows]
        expected = _with_table(exp, len(tables))
        expected["declared_total"] = stated_total  # the total written in the title (spec, not parsed)
        cases.append(Case(name, desc, title, tables, True, expected, list(errors)))

    add("baseline", "the demo layout", CRITERIA)
    add("blank-rows", "empty rows between criteria", CRITERIA, blank_between=True)
    add("merged-header", "a title row merged across the whole table", CRITERIA, header="SPEAKING RUBRIC")
    add("multi-paragraph", "descriptors split over two paragraphs in one cell", CRITERIA, split_cells=True)
    add("second-table", "an unrelated schedule table before the rubric", CRITERIA,
        tables_before=[[["Time", "Part"], ["10 min", "Preparation"], ["1-2 min", "Presentation"]]])
    add("korean", "Korean names and descriptors, total written as 총점", KOREAN, title="말하기 평가 루브릭 총점: /30",
        stated_total=30)
    four_band = [("A", "LANGUAGE", [3, 6, 9, 12], [CRITERIA[0][3][i] for i in (0, 2, 4, 5)])] + list(CRITERIA[1:])
    add("four-bands", "one criterion with four bands (3/6/9/12)", four_band)
    add("descending", "bands listed highest first (12 … 2)", CRITERIA, descending=True)

    add("wrong-total", "document states /40 but criteria add up to /30", CRITERIA,
        title="Speaking Rubric Total: /40", stated_total=40, errors=["/40"])
    missing = [list(c) for c in CRITERIA]
    missing[2] = [missing[2][0], missing[2][1], missing[2][2], list(missing[2][3])]
    missing[2][3][1] = ""
    add("missing-descriptor", "one empty descriptor cell", missing, errors=["no descriptor"])
    dup = [list(c) for c in CRITERIA]
    dup[3] = [dup[3][0], dup[3][1], dup[3][2], list(dup[3][3])]
    dup[3][3][4] = dup[3][3][3]
    add("duplicate-descriptor", "a copy-pasted descriptor", dup, errors=["identical descriptors"])

    # Out of scope: one row per band. Must be reported, not silently mis-read.
    vertical = [["Criterion", "Marks", "Descriptor"]]
    for key, name, marks, descs in CRITERIA:
        for m, d in zip(marks, descs):
            vertical.append([f"{key} {name.title()}", str(m), d])
    cases.append(Case("vertical", "one row per band (layout not supported)", "Speaking Rubric Total: /30",
                      [vertical], expect_extract=False))
    return cases
