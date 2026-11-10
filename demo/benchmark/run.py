"""Run the rubric-extraction benchmark.   python3 -m benchmark.run [--write]

Scores, per case and overall:
- values:      the stated total, criterion names, max marks, band marks and descriptors that match the expected
               result (names compared without regard to letter case; extra or missing items count
               as wrong)
- sources:     source references (table, row, column) that point at the right cell
- validation:  planted errors detected, and no errors raised on clean rubrics
- refusal:     an unsupported layout is reported as unrecognised, never silently mis-read
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from benchmark.cases import Case, all_cases, build_docx
from rubric_pipeline.docx_tables import read_docx
from rubric_pipeline.extract import extract_rubric
from rubric_pipeline.validate import validate

HERE = Path(__file__).resolve().parent


def _norm(s: str) -> str:
    return " ".join(s.split()).casefold()


def score_case(case: Case, workdir: Path) -> dict:
    rubric = extract_rubric(read_docx(build_docx(case, workdir / f"{case.name}.docx")))
    errors = [f.message for f in validate(rubric) if f.level == "ERROR"]
    r = {"case": case.name, "description": case.description, "errors": errors,
         "values": [0, 0], "sources": [0, 0]}
    if not case.expect_extract:
        r["refusal_ok"] = not rubric.criteria and bool(errors)
        r["pass"] = r["refusal_ok"]
        return r
    got = {c.key: c for c in rubric.criteria}
    exp = {c["key"]: c for c in case.expected["criteria"]}
    v, s = r["values"], r["sources"]
    for key, e in exp.items():
        g = got.get(key)
        g_bands = {b.marks: b for b in g.bands} if g else {}
        v[1] += 2; s[1] += 1
        if g:
            v[0] += (_norm(g.name) == _norm(e["name"])) + (g.max_marks == e["max_marks"])
            s[0] += g.name_ref == e["name_ref"]
        for eb in e["bands"]:
            gb = g_bands.get(eb["marks"])
            v[1] += 2; s[1] += 2
            if gb:
                v[0] += 1 + (_norm(gb.descriptor) == _norm(eb["descriptor"]))
                s[0] += (gb.marks_ref == eb["marks_ref"]) + (gb.descriptor_ref == eb["descriptor_ref"])
        extra = set(g_bands) - {b["marks"] for b in e["bands"]}
        v[1] += len(extra)
    v[1] += 2 * len(set(got) - set(exp))  # criteria that should not exist
    v[1] += 1  # the total stated in the document, needed to cross-check the criteria
    v[0] += rubric.declared_total == case.expected["declared_total"]
    detected = [any(x in m for m in errors) for x in case.expected_errors]
    r["planted_errors"] = [sum(detected), len(detected)]
    r["false_alarms"] = 0 if case.expected_errors else len(errors)
    r["pass"] = v[0] == v[1] and s[0] == s[1] and all(detected) and r["false_alarms"] == 0
    return r


def run() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        results = [score_case(c, Path(tmp)) for c in all_cases()]
    tot = lambda k: [sum(r[k][i] for r in results) for i in (0, 1)]  # noqa: E731
    return {"cases": results,
            "summary": {"cases_passed": [sum(r["pass"] for r in results), len(results)],
                        "values": tot("values"), "sources": tot("sources"),
                        "planted_errors_detected": [sum(r.get("planted_errors", [0, 0])[i] for r in results) for i in (0, 1)],
                        "false_alarms": sum(r.get("false_alarms", 0) for r in results),
                        "refusals_ok": [sum(r.get("refusal_ok", False) for r in results),
                                        sum("refusal_ok" in r for r in results)]}}


def report(res: dict) -> str:
    pct = lambda a, b: f"{a}/{b} ({100 * a / b:.1f}%)" if b else "–"  # noqa: E731
    s = res["summary"]
    lines = ["| Case | What it tests | Values | Sources | Validation | Result |", "|---|---|---|---|---|---|"]
    for r in res["cases"]:
        if "refusal_ok" in r:
            val = "reported as unrecognised" if r["refusal_ok"] else "NOT reported"
            lines.append(f"| {r['case']} | {r['description']} | – | – | {val} | {'PASS' if r['pass'] else 'FAIL'} |")
            continue
        if r["planted_errors"][1]:
            val = f"{r['planted_errors'][0]}/{r['planted_errors'][1]} planted errors caught"
        else:
            val = "no false alarm" if not r["false_alarms"] else f"{r['false_alarms']} false alarm(s)"
        lines.append(f"| {r['case']} | {r['description']} | {pct(*r['values'])} | {pct(*r['sources'])} | {val} | "
                     f"{'PASS' if r['pass'] else 'FAIL'} |")
    lines += ["", f"**Cases passed:** {pct(*s['cases_passed'])} · **values:** {pct(*s['values'])} · "
              f"**sources:** {pct(*s['sources'])} · **planted errors caught:** {pct(*s['planted_errors_detected'])} · "
              f"**false alarms:** {s['false_alarms']} · **unsupported layouts reported:** {pct(*s['refusals_ok'])}"]
    return "\n".join(lines)


if __name__ == "__main__":
    res = run()
    print(report(res))
    if "--write" in sys.argv:
        (HERE / "results.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for r in res["cases"]:
        if not r["pass"] and r["errors"]:
            print(f"\n{r['case']}: " + " | ".join(r["errors"][:3]))
