# Backlog (after the first application)

None of these are needed before applying. Ordered by value for the Document AI direction.

| # | Item | Done when | Size |
|---|---|---|---|
| 1 | **Small document-extraction benchmark** | 20–30 synthetic + public rubrics and forms (DOCX, PDF, scanned), each with hand-made expected JSON. Report field-level exact match, source-reference correctness and "unrecognised" rate, with the same script on every change. | 2–3 days |
| 2 | **Speaker and Q&A regression fixes** | Regression tests from the pilot's failure patterns (mixed speakers, the missed Q&A boundary), using synthetic audio. The drafted automatic-count + micro-speaker merge fix is merged and re-run on the same five recordings. Speaker accuracy measured against teacher-annotated turns. | 3–5 days |
| 3 | **Ubuntu deployment evidence for the portable parts** | Docker image (or plain venv recipe) for the server, knowledge index, search and evaluation modules on Ubuntu, with a faster-whisper/CPU or CUDA speech backend. A deployment note with real timings. macOS-only parts (MLX, Vision OCR) are listed with their Linux replacements. | 2–3 days |
| 4 | **Small PyTorch training experiment** | A reproducible notebook/script, e.g. fine-tune a small layout or token-classification model on a public form dataset (such as FUNSD), with a held-out evaluation, presented honestly as a learning project. | 3–4 days |
| 5 | **Human-verified English/Korean transcription evaluation** | With school approval: teachers correct 10 English + 10 Korean transcripts while listening (post-edited references, bias noted), and 2–3 are transcribed from scratch. Report WER (English) and CER (Korean) with exact scope. The evaluation module for this already exists in localEd. | 2–3 weeks of teacher time |

Smaller items found along the way:
- Teacher approval tied to the signed-in Chat user, and every rubric-based step refusing unapproved rubrics,
  inside localEd itself (the demo's gate, integrated).
- Replace the placeholder rubric on the server with the extracted, approved speaking rubric.
- The Whisper hint only reaches the first 30 seconds of audio; measure whether a hint helps at
  all once human references exist.
