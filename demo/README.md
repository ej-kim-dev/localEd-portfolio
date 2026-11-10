# Demo: from a teacher's request to an approved, structured rubric

**Workflow:** teacher request → authorized retrieval with citations → table-aware structured
extraction → validation → document outputs → teacher approval before the rubric can be used.

```bash
python3 -m rubric_pipeline demo                        # whole workflow, about 1 second
python3 -m unittest discover -s tests -v               # 16 tests (incl. the benchmark)
python3 -m benchmark.run                               # 12-case extraction benchmark
python3 -m rubric_pipeline extract sample_drive/allowed/assessment/speaking_rubric_synthetic.docx
python3 -m rubric_pipeline approve out/speaking_rubric_synthetic.json --by "Ms Teacher"
python3 -m rubric_pipeline check-gate out/speaking_rubric_synthetic.json
```

Python 3.10+ and the standard library only. Run the commands from this `demo/` folder.

## What is real, what is simulated

| Step | In this demo | In localEd (private) |
|---|---|---|
| Teacher request | a fixed sentence (**simulated**) | Google Chat message via Pub/Sub |
| Authorization | local folder allow-list, blocks `../` and symlinks (**real logic, local files**) | Drive folder allow-list + domain check |
| Retrieval | keyword ranking with file + position citations (**real, simple**) | hybrid vector + keyword search over an index |
| Extraction | table-aware DOCX reader with cell-level sources (**real; this is the new part**) | today's reader flattens tables (see below) |
| Validation | explicit rules, located errors (**real**) | not yet present |
| Outputs | JSON, localEd-format Markdown, HTML review page (**real, local files**) | uploaded as Google Docs |
| Approval gate | SHA-256 fingerprint of the approved file (**real logic**, typed teacher name) | teacher = signed-in Chat user (to build) |
| Language model | **not used**: extraction is deterministic | local LLM chooses tools and drafts suggestions for teachers |

## Why this step

localEd's current Word reader was built for search. On `speaking_rubric_synthetic.docx` it
produces 58 separate paragraphs (`A`, `2`, `4` … `LANGUAGE`, descriptor, descriptor …), so the
link between a band's marks and its descriptor is lost. Teachers' assessment needs that link to be exact
and checkable, so this reader keeps the table structure and cites the source cell of every value.

## Files

- `rubric_pipeline/docx_tables.py`: reads paragraphs and tables (rows, columns, merged cells)
  from `.docx` with `zipfile` + `xml`.
- `rubric_pipeline/extract.py`: recognises the rubric layout (marks row + descriptor row per
  criterion). Anything else is reported, not guessed.
- `rubric_pipeline/validate.py`: rules a teacher can read; errors block approval.
- `rubric_pipeline/approval.py`: approval tied to the exact file contents.
- `rubric_pipeline/retrieval.py`: allow-list check and cited keyword search.
- `rubric_pipeline/render.py`: JSON, Markdown in localEd's rubric format, HTML review page.
- `rubric_pipeline/samples.py`: creates the synthetic sample "Drive" (`sample_drive/`).

All sample content was written for this demo. The descriptors are original wording, not taken from any exam
board, and no student or school data is included.

## Benchmark

[benchmark/](benchmark/README.md): 12 synthetic cases covering blank rows, merged header cells,
multi-paragraph cells, a second table, Korean text, four-band criteria, descending marks,
three planted errors, and an unsupported layout. The first run found two bugs (descending
marks raised false errors; the Korean total "총점" was missed). Both are fixed and the run now
passes 12/12. Both runs are reported there.

## Known limits

- One table layout is recognised (marks row + descriptor row). Rubrics with one row per band, or
  with vertically merged cells, are reported as unrecognised rather than parsed.
- `.docx` only. PDF and scanned rubrics would need a layout-aware parser.
- Retrieval is keyword-based; it demonstrates the citation contract, not search quality.
