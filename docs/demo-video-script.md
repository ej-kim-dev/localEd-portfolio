# Demo video script (about 2½ minutes)

Record in one take with a terminal and a browser side by side. Use only this repository's
synthetic files. Do not show the private repository, Google accounts, or any school or student
documents.

| Time | Screen | Say (adapt freely) |
|---|---|---|
| 0:00–0:20 | README, architecture diagram | "I teach at a private school in Korea. I built localEd, an AI assistant that runs entirely on one Mac inside the school. Teachers ask for things in Google Chat; it reads school documents, transcribes oral assessments and organizes rubric evidence for teachers, and writes the results back to Google Drive." |
| 0:20–0:45 | `docs/evidence.md`, section 1 | "In a pilot on five English oral assessments, 24 minutes of audio, all five runs completed in about three minutes. The benchmark also found real failures: mixed speaker labels, a missed Q&A boundary, and a placeholder rubric for the wrong assessment. I don't claim an accuracy figure yet, because there is no human-checked reference." |
| 0:45–1:00 | `demo/README.md`, the "what is real" table | "That rubric failure is a document problem, so this demo shows the fix. It runs locally, uses synthetic files, and needs no installs." |
| 1:00–1:50 | terminal: `python3 -m rubric_pipeline demo` (scroll slowly) | Step 2: "A file outside the allowed folders is refused, even through `../`." Step 3: "Retrieval cites the file and the position of each match." Step 4: "The table becomes four criteria, each band with its marks and its descriptor, and every value names its source cell." Step 5: "A broken draft gives three precise errors instead of a guess." Step 6: "The rubric can't be used until a teacher approves this exact file. Edit it afterwards, and it's blocked again." |
| 1:50–2:10 | browser: `out/speaking_rubric_synthetic.review.html` | "This is the page the teacher reviews: every descriptor next to the cell it came from, plus the validation results." |
| 2:10–2:25 | terminal: `python3 -m unittest discover -s tests -v` | "Sixteen tests cover the reader, extraction, validation, access control and the approval gate, and a 12-case benchmark, including Korean, runs with them. Its first run found two bugs, which I fixed and reported." |
| 2:25–2:40 | case study PDF, last section | "Next, I'll benchmark extraction on synthetic and public forms, field by field and source by source, and fix the speaker and Q&A regressions using human-checked transcripts." |

Tips: increase the terminal font size, clear the screen before each command, and keep the
browser zoom at about 125%.
