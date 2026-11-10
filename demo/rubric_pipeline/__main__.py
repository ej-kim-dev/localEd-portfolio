"""Command line for the rubric demo.

    python -m rubric_pipeline demo                 # the whole workflow, step by step
    python -m rubric_pipeline extract FILE.docx    # extract + validate one rubric
    python -m rubric_pipeline approve OUT.json --by "Ms Teacher"
    python -m rubric_pipeline check-gate OUT.json  # may this rubric be used?

Everything runs locally on synthetic files. Nothing is sent anywhere.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from rubric_pipeline import approval, render
from rubric_pipeline.docx_tables import read_docx
from rubric_pipeline.extract import ExtractedRubric, extract_rubric
from rubric_pipeline.retrieval import AccessDenied, check_access, search
from rubric_pipeline.samples import DEMO_DIR, DRIVE, make_samples
from rubric_pipeline.validate import has_errors, validate

OUT = DEMO_DIR / "out"
PENDING = "PENDING TEACHER APPROVAL - not usable yet"


def step(n: int, title: str, kind: str) -> None:
    print(f"\n[{n}] {title}  ({kind})")


def extract_and_write(path: Path, out_dir: Path) -> tuple[Path, bool]:
    rubric = extract_rubric(read_docx(path))
    findings = validate(rubric)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = path.stem
    json_path = render.write_json(rubric, out_dir / f"{stem}.json")
    (out_dir / f"{stem}.md").write_text(render.to_localed_markdown(rubric), encoding="utf-8")
    (out_dir / f"{stem}.review.html").write_text(render.to_review_html(rubric, findings, PENDING),
                                                 encoding="utf-8")
    print(f"    {len(rubric.criteria)} criteria, total /{rubric.total} "
          f"(document states /{rubric.declared_total})")
    for c in rubric.criteria:
        print(f"    - {c.key}: {c.name} (max {c.max_marks}), {len(c.bands)} bands, name from {c.name_ref}")
    for f in findings:
        print(f"    {f.level}: {f.message}")
    if not findings:
        print("    validation: no issues")
    return json_path, has_errors(findings)


def demo() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    make_samples()
    allowed = [DRIVE / "allowed"]
    request = "Please prepare the speaking assessment rubric so I can use it"

    step(1, "Teacher request", "simulated chat message")
    print(f'    "{request}"')

    step(2, "Authorization", "local check; stands in for localEd's Drive allow-list")
    print(f"    readable folders: {[str(p.relative_to(DEMO_DIR)) for p in allowed]}")
    try:
        check_access(DRIVE / "restricted" / "marks_synthetic.md", allowed)
    except AccessDenied as exc:
        print(f"    refused as expected: {exc}")
    try:
        check_access(DRIVE / "allowed" / ".." / "restricted" / "marks_synthetic.md", allowed)
    except AccessDenied:
        print("    refused as expected: the same file reached through 'allowed/../' is also blocked")

    step(3, "Retrieval with citations", "local keyword search over the allowed folder")
    hits = search(request, allowed)
    for i, h in enumerate(hits, 1):
        print(f"    [{i}] {h.path.name} - {h.where} (score {h.score}): \"{h.snippet}\"")
    # Selection rule (printed, not hidden): the best-ranked Word rubric whose title is not a draft.
    chosen = next((h for h in hits if h.path.suffix == ".docx"
                   and "draft" not in h.snippet.lower()), None)
    if chosen is None:
        print("    no final rubric found; localEd would ask the teacher which file to use")
        return 1
    print(f"    rule: best-ranked .docx not titled DRAFT -> [{hits.index(chosen) + 1}] {chosen.path.name}")
    chosen = chosen.path

    step(4, "Structured extraction + validation", "local, deterministic, no language model")
    good_json, good_errors = extract_and_write(chosen, OUT)

    step(5, "Same pipeline on a broken draft", "shows that errors are caught, not guessed")
    bad_json, bad_errors = extract_and_write(DRIVE / "allowed" / "assessment" / "speaking_rubric_draft_errors.docx", OUT)

    step(6, "Teacher approval gate", "local; in localEd the teacher is the signed-in Chat user")
    for path, errors in ((good_json, good_errors), (bad_json, bad_errors)):
        try:
            approval.require_approval(path)
        except approval.NotApproved as exc:
            print(f"    {path.stem}: use blocked - {exc}")
    try:
        approval.approve(bad_json, "Ms Teacher (synthetic)", bad_errors)
    except approval.NotApproved as exc:
        print(f"    approving the broken draft is refused: {exc}")
    approval.approve(good_json, "Ms Teacher (synthetic)", good_errors)
    record = approval.require_approval(good_json)
    print(f"    {good_json.stem}: approved by {record['approved_by']}; use allowed")
    good_json.write_text(good_json.read_text(encoding="utf-8").replace('"max_marks": 12', '"max_marks": 14'),
                         encoding="utf-8")
    try:
        approval.require_approval(good_json)
    except approval.NotApproved as exc:
        print(f"    after an edit to the approved file: use blocked - {exc}")

    step(7, "Requested documents", "local files; localEd would upload these to Google Docs")
    for p in sorted(OUT.iterdir()):
        print(f"    {p.relative_to(DEMO_DIR)}")
    print("\nNot shown here (needs the private system): the local LLM agent choosing these tools, "
          "and Google Drive/Docs/Chat.")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="rubric_pipeline")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("demo")
    e = sub.add_parser("extract"); e.add_argument("file", type=Path); e.add_argument("--out", type=Path, default=OUT)
    a = sub.add_parser("approve"); a.add_argument("json", type=Path); a.add_argument("--by", required=True)
    g = sub.add_parser("check-gate"); g.add_argument("json", type=Path)
    args = ap.parse_args(argv)
    if args.cmd == "demo":
        return demo()
    if args.cmd == "extract":
        _, errors = extract_and_write(args.file, args.out)
        return 1 if errors else 0
    if args.cmd == "approve":
        rubric = ExtractedRubric.from_dict(json.loads(args.json.read_text(encoding="utf-8")))
        try:  # validation is re-run on the exact file being approved
            print(f"approved: {approval.approve(args.json, args.by, has_errors(validate(rubric)))}")
            return 0
        except approval.NotApproved as exc:
            print(f"refused: {exc}")
            return 1
    if args.cmd == "check-gate":
        try:
            r = approval.require_approval(args.json)
            print(f"rubric use allowed (approved by {r['approved_by']})"); return 0
        except approval.NotApproved as exc:
            print(f"rubric use blocked: {exc}"); return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
