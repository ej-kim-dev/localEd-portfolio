"""Tests for the rubric demo. Run from demo/:  python -m unittest discover -s tests -v"""

import json
import os
import re
import tempfile
import unittest
import zipfile
from pathlib import Path

from rubric_pipeline import approval, render
from rubric_pipeline.docx_tables import DocxError, read_docx
from rubric_pipeline.extract import ExtractedRubric, extract_rubric
from rubric_pipeline.retrieval import AccessDenied, check_access, search
from rubric_pipeline.samples import CRITERIA, make_samples, rubric_rows, write_docx
from rubric_pipeline.validate import has_errors, validate


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.files = make_samples(self.dir / "drive")

    def tearDown(self):
        self.tmp.cleanup()


class ReadDocx(Base):
    def test_tables_keep_rows_columns_and_positions(self):
        content = read_docx(self.files["good"])
        self.assertEqual(len(content.tables), 1)
        rows = content.tables[0].rows
        self.assertEqual([c.text for c in rows[0]], ["A", "2", "4", "6", "8", "10", "12"])
        self.assertEqual(rows[1][3].ref, "table 1, row 2, column 4")
        self.assertIn("Total: /30", content.paragraphs[0])

    def test_merged_cells_keep_their_grid_column(self):
        path = self.dir / "span.docx"
        write_docx(path, "t", [["A", "2", "4"], ["NAME", "x"]])
        # widen the descriptor cell to cover two grid columns
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode()
        xml = xml.replace("<w:tcPr><w:tcW w:w=\"1500\" w:type=\"dxa\"/></w:tcPr><w:p><w:r><w:t xml:space=\"preserve\">x",
                          "<w:tcPr><w:gridSpan w:val=\"2\"/></w:tcPr><w:p><w:r><w:t xml:space=\"preserve\">x", 1)
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("word/document.xml", xml)
        cell = read_docx(path).tables[0].rows[1][1]
        self.assertEqual((cell.col, cell.span), (2, 2))

    def test_not_a_docx_is_a_clear_error(self):
        bad = self.dir / "x.docx"
        bad.write_bytes(b"not a zip")
        with self.assertRaises(DocxError):
            read_docx(bad)


class Extract(Base):
    def test_valid_rubric_is_fully_structured_with_sources(self):
        r = extract_rubric(read_docx(self.files["good"]))
        self.assertEqual([c.key for c in r.criteria], ["A", "B1", "B2", "C"])
        self.assertEqual([c.max_marks for c in r.criteria], [12, 6, 6, 6])
        self.assertEqual((r.total, r.declared_total), (30, 30))
        band = r.criteria[0].bands[2]
        self.assertEqual(band.marks, 6)
        self.assertEqual(band.descriptor, CRITERIA[0][3][2])
        self.assertEqual((band.marks_ref, band.descriptor_ref),
                         ("table 1, row 1, column 4", "table 1, row 2, column 4"))
        self.assertEqual(validate(r), [])

    def test_round_trip_through_json(self):
        r = extract_rubric(read_docx(self.files["good"]))
        again = ExtractedRubric.from_dict(json.loads(json.dumps(r.to_dict())))
        self.assertEqual(again.to_dict(), r.to_dict())

    def test_unrecognised_layout_is_reported_not_guessed(self):
        path = write_docx(self.dir / "odd.docx", "Notes", [["Criterion", "Marks"], ["Language", "twelve"]])
        r = extract_rubric(read_docx(path))
        self.assertEqual(r.criteria, [])
        self.assertTrue(has_errors(validate(r)))


class Validate(Base):
    def test_broken_draft_reports_each_problem_with_its_location(self):
        findings = validate(extract_rubric(read_docx(self.files["broken"])))
        messages = [f.message for f in findings if f.level == "ERROR"]
        self.assertEqual(len(messages), 3)
        self.assertTrue(any("B1" in m and "row 3, column 5" in m for m in messages))
        self.assertTrue(any("identical descriptors" in m for m in messages))
        self.assertTrue(any("/40" in m and "/30" in m for m in messages))

    def test_marks_must_increase_and_keys_be_unique(self):
        crit = [list(c) for c in CRITERIA]
        crit[0][2] = [2, 4, 4, 8, 10, 12]
        crit[1][0] = "A"
        path = write_docx(self.dir / "dup.docx", "Rubric Total: /30", rubric_rows(crit))
        messages = " ".join(f.message for f in validate(extract_rubric(read_docx(path))))
        self.assertIn("strictly increase", messages)
        self.assertIn("appears more than once", messages)


class Access(Base):
    def test_only_allowed_folders_can_be_read(self):
        allowed = [self.dir / "drive" / "allowed"]
        self.assertTrue(check_access(self.files["good"], allowed))
        with self.assertRaises(AccessDenied):
            check_access(self.files["restricted"], allowed)
        with self.assertRaises(AccessDenied):
            check_access(allowed[0] / ".." / "restricted" / "marks_synthetic.md", allowed)

    @unittest.skipIf(os.name == "nt", "symlinks need admin rights on Windows")
    def test_symlink_out_of_the_allowed_folder_is_refused(self):
        allowed = self.dir / "drive" / "allowed"
        link = allowed / "assessment" / "sneaky.md"
        link.symlink_to(self.files["restricted"])
        with self.assertRaises(AccessDenied):
            search("marks", [allowed])

    def test_search_cites_file_and_position_and_never_returns_restricted_files(self):
        allowed = [self.dir / "drive" / "allowed"]
        hits = search("speaking assessment rubric", allowed)
        self.assertTrue(hits)
        self.assertTrue(all("restricted" not in str(h.path) for h in hits))
        self.assertTrue(all(re.match(r"(paragraph|table|line) \d+", h.where) for h in hits))
        self.assertIn("rubric", hits[0].path.name)


class ApprovalGate(Base):
    def setUp(self):
        super().setUp()
        self.rubric = extract_rubric(read_docx(self.files["good"]))
        self.json = render.write_json(self.rubric, self.dir / "rubric.json")

    def test_grading_requires_approval_of_the_exact_file(self):
        with self.assertRaises(approval.NotApproved):
            approval.require_approval(self.json)
        approval.approve(self.json, "Teacher", has_errors(validate(self.rubric)))
        self.assertEqual(approval.require_approval(self.json)["approved_by"], "Teacher")
        self.json.write_text(self.json.read_text().replace("Language", "Languag"))
        with self.assertRaisesRegex(approval.NotApproved, "changed after it was approved"):
            approval.require_approval(self.json)

    def test_rubrics_with_errors_or_without_a_name_cannot_be_approved(self):
        with self.assertRaises(approval.NotApproved):
            approval.approve(self.json, "Teacher", has_errors=True)
        with self.assertRaises(approval.NotApproved):
            approval.approve(self.json, "  ", has_errors=False)

    def test_vertical_merge_blocks_approval_even_when_criteria_are_recognized(self):
        path = self.files["good"]
        with zipfile.ZipFile(path) as z:
            entries = [(info, z.read(info.filename)) for info in z.infolist()]
        with zipfile.ZipFile(path, "w") as z:
            for info, content in entries:
                if info.filename == "word/document.xml":
                    content = content.replace(b"<w:tcPr>", b'<w:tcPr><w:vMerge w:val="restart"/>', 1)
                z.writestr(info, content)
        rubric = extract_rubric(read_docx(path))
        self.assertEqual(len(rubric.criteria), 4)
        findings = validate(rubric)
        self.assertTrue(any(f.level == "ERROR" and "vertically merged" in f.message for f in findings))
        output = render.write_json(rubric, self.dir / "merged.json")
        with self.assertRaises(approval.NotApproved):
            approval.approve(output, "Teacher", has_errors(validate(rubric)))


class Outputs(Base):
    def test_markdown_matches_the_localed_rubric_format(self):
        md = render.to_localed_markdown(extract_rubric(read_docx(self.files["good"])))
        headings = re.findall(r"^## Criterion (\w+): (.+) \(max (\d+)\)$", md, re.M)
        self.assertEqual([(k, int(m)) for k, _, m in headings], [("A", 12), ("B1", 6), ("B2", 6), ("C", 6)])
        self.assertIn("total_max: 30", md)
        self.assertIn("source: table 1, row 2, column 2", md)

    def test_review_page_is_labelled_and_escapes_text(self):
        r = extract_rubric(read_docx(self.files["good"]))
        r.criteria[0].bands[0].descriptor = "<script>x</script>"
        html = render.to_review_html(r, validate(r), "PENDING TEACHER APPROVAL")
        self.assertIn("PENDING TEACHER APPROVAL", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>x", html)


if __name__ == "__main__":
    unittest.main()
