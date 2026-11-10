# Evidence: what is measured, what is not

Every claim in this portfolio points here. The source code of localEd is in a private repository
because it runs on school data; the numbers below are aggregate figures that contain no student
information.

## 1. Pilot benchmark: five English oral-assessment recordings (10 Nov 2026)

**Scope.** Five practice (Pre-DP) English B speaking assessments, 24 min 15.36 s of audio in total,
processed once each on the school's Apple M4 Max (36 GiB RAM) with models already cached.
Run and reported by a separate benchmark agent (Codex), not by me by hand.

| Measure | Result |
|---|---|
| Pipeline runs completed | **5 of 5** |
| Total pipeline time | **180.61 s** for 24 min 15 s of audio (about 8× faster than real time; 36.1 s per recording on average) |
| What the pipeline time includes | Drive reads and downloads, audio decoding, Whisper ASR, local-LLM Q&A detection, speaker diarization, self-introduction name check, document rendering |
| What it excludes | Creating/sharing the Google Docs and the Google Chat round trip |
| Speech recognition only (Whisper large-v3-turbo, MLX) | **39.75 s** |
| Speech recognition, full Whisper large-v3 baseline | **78.23 s** (about 2× the turbo time) |
| Recordings where a teacher-Q&A boundary was emitted | 4 of 5 |
| Word timestamps with an invalid start/end interval | 0 of 2,660 (checks validity, not timing accuracy) |

**Failures found by the benchmark** (these drive the backlog):
- Speaker blocks mixed teacher questions and student answers; speaker labels cannot yet be used to
  filter "student only" speech.
- One recording got no Q&A boundary although its own transcript contains the teacher's questions.
- The grading rubric configured on the server was a placeholder for a *different* assessment
  (/40 instead of the speaking rubric's /30). Grading was therefore not run, and no marks were issued.

**Not measured (do not infer these):** word error rate against a human reference, speaker-attribution
accuracy, timing accuracy, grading agreement with teachers, teacher review time, Korean performance,
behaviour under concurrent load or at production scale.

## 2. Software quality checks

| Check | Result | Scope |
|---|---|---|
| localEd automated test suite | **225 passed**, 1 skipped | Linux, Python 3.13, 10 Nov 2026, private repo commit `cc8757a`. macOS-only parts (MLX Whisper, Vision OCR) are not exercised on Linux. |
| This portfolio's demo tests | **16 passed** | `python3 -m unittest discover -s tests` in `demo/`, standard library only |
| Demo output loads in localEd's real rubric loader | **Yes**: 4 criteria, total 30, no placeholders | checked against private commit `cc8757a` |
| Demo's generated Word file opens in LibreOffice | **Yes** | LibreOffice headless conversion |

## 3. A document-processing gap found while preparing this portfolio

localEd's Word reader (built for search) turns a `.docx` into paragraphs. On the synthetic rubric in
`demo/`, it produces **58 separate paragraphs**: the band marks (`2`, `4`, `6` …) end up far from the
descriptors they belong to, so the table's meaning is lost. That is acceptable for keyword and
vector search, but not for extracting a rubric that grading will depend on. The demo in this
repository is the fix I am proposing: a table-aware reader that keeps every cell's position, so
each extracted value can cite its source.

## 4. Workload context (not results)

The school's intended annual oral-assessment workload is about **240 recordings** (≈180 English,
≈60 Korean). About 120 English and 30 Korean recordings exist as materials. They have **not** been
processed or validated with localEd. At the pilot's average of 36 s per recording, 240 recordings
would take roughly 2.4 hours of machine time. That is a projection from five English recordings,
not a measurement, and Korean performance is untested.

## 5. Claims this portfolio deliberately does not make

- No accuracy percentage for transcription (there is no human-verified reference yet).
- No comparison claim against any commercial transcription service.
- No claim of validated grading, bilingual (Korean) grading, or teacher time saved.
- No claim of model training or fine-tuning: localEd uses existing open models.
