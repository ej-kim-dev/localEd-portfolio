# Rubric-extraction benchmark (synthetic)

```bash
python3 -m benchmark.run          # from demo/; add --write to save results.json
```

**12 cases**, each a generated `.docx` whose expected output comes from the spec used to build it
(where each value was placed), not from the extractor. Cases cover layout variations found in
real school documents, planted errors the validator must catch, and one layout the extractor does
not support, which it must report rather than mis-read.

| What is scored | How |
|---|---|
| **Values** | stated total, criterion names (letter case ignored), max marks, band marks, descriptors; missing or extra items count as wrong |
| **Sources** | every name, mark and descriptor points at the right table, row and column |
| **Validation** | planted errors are caught; clean rubrics raise no errors |
| **Refusal** | the unsupported layout produces "unrecognised", not a wrong rubric |

## Results

| Run | Cases passed | Values | Sources | Planted errors caught | False alarms | Unsupported layout reported |
|---|---|---|---|---|---|---|
| 1: extractor as first written | 10/12 | 622/623 | 568/568 | 3/3 | **4** | 1/1 |
| 2: after the two fixes below | **12/12** | **623/623** | **568/568** | **3/3** | **0** | **1/1** |

What run 1 found, and what changed:
1. **`descending`:** rubrics that list the highest band first (12, 10 … 2) produced 4 false
   errors. Validation assumed ascending order; it now accepts either direction if consistent.
2. **`korean`:** the stated total "총점: /30" was not recognised, so the total check was silently
   skipped. Writing this benchmark also exposed a gap in the benchmark itself: the first version
   didn't score the stated total at all, which hid this failure. The total is now a scored field,
   and the extractor reads "총점" as well as "Total".

Per-case results: [results.json](results.json) (run 2).

## Limits: read before quoting these numbers

- **The cases are synthetic, and I wrote them knowing how the extractor works.** They measure
  robustness to known variations and catch regressions. They are not an estimate of accuracy on
  real rubrics.
- Only `.docx` tables. No PDFs, scans, images or HWP files.
- One layout family (marks row + descriptor row). Other layouts are refused, by design.
- **Next:** add public rubrics and forms (several layouts and file types) with hand-checked
  expected output, and keep run-to-run results in this file.
