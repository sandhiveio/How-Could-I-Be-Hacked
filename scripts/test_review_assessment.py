"""Behavioral checks for retrieval provenance, revision pins and derived review totals."""
import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

import review_assessment as review
from toolkit import validate_assessment


class ReviewAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.library = self.root / "library"
        self.library.mkdir()
        self.path = self.root / "assessment.json"
        self.head = "a" * 40
        self.base = "b" * 40
        case = "case-" + "c" * 32
        self.records = [{"kind": "curated_case", "case_id": case,
                         "iteration_id": step, "candidate": {"id": cid, "text": "authorization fixture"},
                         "selected_in_source_case": False, "historical_observation": None}
                        for step, cid in [("iteration-0001", "candidate-a"),
                                          ("iteration-0001", "candidate-b"),
                                          ("iteration-0002", "candidate-c")]]
        with closing(sqlite3.connect(self.library / "index.sqlite")) as db, db:
            db.execute("CREATE VIRTUAL TABLE examples USING fts5(search_text, record UNINDEXED)")
            for record in self.records:
                db.execute("INSERT INTO examples VALUES (?, ?)", ("authorization fixture", json.dumps(record)))
        for ordinal in ("0001", "0002"):
            folder = self.library / "cases" / case / "iterations" / ordinal
            folder.mkdir(parents=True)
            (folder / "step.json").write_text("{}", encoding="utf-8")
        self.doc = review.scaffold("temporary review fixture", "pr", self.base, self.head, self.library,
                                   {"cases": 1, "steps": 2, "search_entries": 3})
        self.doc["scope"] = "Synthetic validator fixture, no target security claim"
        self.save()

    def save(self, doc=None):
        self.path.write_text(json.dumps(self.doc if doc is None else doc), encoding="utf-8")

    def retrieve(self, query="authorization"):
        result = review.record_search(self.path, self.library, query, None, 5)
        self.doc = json.loads(self.path.read_text(encoding="utf-8"))
        return result

    def decisions(self):
        self.doc["decisions"] = [{"source_id": review.source_id(record),
                                   "applicability": "Matches this synthetic fixture",
                                   "reason": "Use the fixture to verify reporting", "selected": True}
                                  for record in self.records]

    def check(self, cid, sources, status="supported", origin="library"):
        check = {"id": cid, "origin": origin, "source_ids": sources,
                 "code_locations": ["fixture.py:1"], "hypothesis": "Fixture result is recorded",
                 "adaptation": "Map the source assertion to a synthetic validator fixture",
                 "test": "Read the synthetic result artifact", "expected": "Fixture text exists",
                 "falsifier": "Missing fixture text", "control": "An unrelated fixture",
                 "status": status, "revision": self.head, "evidence": []}
        if status == "not_executed":
            check["reason"] = "Deliberately pending in this unit-test fixture"
        else:
            output = self.root / (cid + ".txt")
            output.write_text("Synthetic unit-test output, no target security evidence", encoding="utf-8")
            check["evidence"] = [{"command": "unit-test fixture", "exit_code": 0,
                                   "output_artifact": output.name, "sha256": review.digest(output),
                                   "interpretation": "Synthetic fixture only"}]
        return check

    def ready(self):
        self.retrieve()
        self.decisions()
        sid = review.source_id(self.records[0])
        self.doc["checks"] = [self.check("check-1", [sid])]
        self.save()

    def test_deduplicated_sources_and_many_to_many_checks(self):
        self.retrieve()
        self.retrieve("authorization fixture")
        self.decisions()
        first, second, third = [review.source_id(record) for record in self.records]
        self.doc["checks"] = [self.check("combined", [first, second]),
                              self.check("reused", [first], status="refuted"),
                              self.check("pending", [third], status="not_executed")]
        self.save()
        self.assertTrue(validate_assessment(self.path)["ok"])
        counts = review.report(self.path)["counts"]
        self.assertEqual((counts["searches"], counts["retrieved_entries"], counts["retrieved_steps"]), (2, 3, 2))
        self.assertEqual((counts["considered_entries"], counts["selected_entries"], counts["used_entries"]), (3, 3, 2))
        self.assertEqual((counts["selected_steps"], counts["used_steps"]), (2, 1))
        self.assertEqual((counts["executed_checks"], counts["pending_checks"]), (2, 1))
        self.assertEqual(counts["outcomes"]["refuted"], 1)
        report = review.report(self.path)
        self.assertEqual(len(report["sources"]), 3)
        self.assertEqual(len(report["searches"]), 2)
        self.assertIn("historical_observation", report["sources"][0])
        rendered = review.markdown(report)
        check = self.doc["checks"][0]
        for field in ("hypothesis", "test", "expected", "falsifier", "control"):
            self.assertIn(check[field], rendered)
        self.assertIn(check["evidence"][0]["command"], rendered)
        self.assertIn(check["evidence"][0]["interpretation"], rendered)
        self.assertIn((self.root / "combined.txt").resolve().as_posix(), rendered)
        self.assertIn(self.base, rendered)

    def test_no_hits_and_local_analysis_are_valid(self):
        self.retrieve("absent mechanism")
        self.doc["checks"] = [self.check("local", [], origin="local_analysis")]
        self.doc["gaps"] = ["Fixture covers no deployed environment"]
        self.save()
        counts = review.report(self.path)["counts"]
        self.assertEqual(counts["retrieved_entries"], 0)
        self.assertEqual(counts["local_analysis_checks"], 1)
        self.assertEqual(counts["used_entries"], 0)
        self.doc["checks"] = []
        self.save()
        self.assertTrue(validate_assessment(self.path)["ok"])
        self.assertEqual(review.report(self.path)["counts"]["executed_checks"], 0)

    def test_missing_empty_and_changed_execution_evidence_are_rejected(self):
        self.ready()
        output = self.root / "check-1.txt"
        output.write_text("changed result", encoding="utf-8")
        self.assertFalse(validate_assessment(self.path)["ok"])
        output.write_text("", encoding="utf-8")
        self.assertFalse(validate_assessment(self.path)["ok"])
        output.unlink()
        self.assertFalse(validate_assessment(self.path)["ok"])

    def test_stale_receipt_and_query_mismatch_are_rejected(self):
        self.ready()
        entry = self.doc["searches"][0]
        receipt_path = self.root / entry["result_artifact"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["query"] = "different query"
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        self.assertFalse(validate_assessment(self.path)["ok"])
        entry["sha256"] = review.digest(receipt_path)
        self.save()
        self.assertIn("differs from journal", validate_assessment(self.path)["errors"][0])

    def test_unknown_unselected_duplicate_and_wrong_revision_checks_are_rejected(self):
        self.ready()
        for mutation in ("unknown", "unselected", "duplicate", "revision", "pending_evidence", "boolean_exit"):
            with self.subTest(mutation=mutation):
                doc = copy.deepcopy(self.doc)
                check = doc["checks"][0]
                if mutation == "unknown":
                    check["source_ids"] = ["unknown"]
                elif mutation == "unselected":
                    doc["decisions"][0]["selected"] = False
                elif mutation == "duplicate":
                    doc["checks"].append(copy.deepcopy(check))
                elif mutation == "revision":
                    check["revision"] = "d" * 40
                elif mutation == "pending_evidence":
                    check["status"] = "not_executed"
                    check["reason"] = "Fixture"
                else:
                    check["evidence"][0]["exit_code"] = True
                self.save(doc)
                self.assertFalse(validate_assessment(self.path)["ok"])

    def test_snapshot_update_blocks_retrieval_without_replacing_existing_receipts(self):
        first = self.retrieve()
        output = Path(first["result_artifact"])
        previous = output.read_bytes()
        with closing(sqlite3.connect(self.library / "index.sqlite")) as db, db:
            db.execute("INSERT INTO examples VALUES ('extra', ?)", (json.dumps(self.records[0]),))
        with self.assertRaisesRegex(ValueError, "snapshot changed"):
            self.retrieve()
        self.assertEqual(output.read_bytes(), previous)
        self.assertEqual(len(json.loads(self.path.read_text())["searches"]), 1)

    def test_legacy_assessment_keeps_validation(self):
        output = self.root / "legacy.txt"
        output.write_text("legacy fixture", encoding="utf-8")
        doc = {"schema_version": 1, "target": "fixture", "scope": "fixture", "hypotheses": [{
            "id": "legacy", "hypothesis": "Fixture", "applicability": "Fixture", "test": "Fixture",
            "expected": "Fixture", "falsifier": "Fixture", "control": "Fixture",
            "source_references": ["legacy source"], "code_locations": ["fixture.py:1"],
            "status": "supported", "evidence": [{"command": "fixture", "output_artifact": output.name,
                                                     "interpretation": "Fixture"}]}]}
        self.save(doc)
        self.assertTrue(validate_assessment(self.path)["ok"])

    def test_normal_cli_entry_points_and_malformed_records(self):
        tool = Path(__file__).with_name("toolkit.py")
        initialized = self.root / "cli.json"
        common = [sys.executable, str(tool), "--library", str(self.library)]
        result = subprocess.run([*common, "init-assessment", "--mode", "pr", "--base", self.base,
                                 "--head", self.head, "--target", "fixture", "--out", str(initialized)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        doc = json.loads(initialized.read_text())
        doc["scope"] = "No target behavior checked in unit-test fixture"
        initialized.write_text(json.dumps(doc), encoding="utf-8")
        result = subprocess.run([*common, "search-assessment", "--file", str(initialized),
                                 "--query", "authorization"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for format_value in ("json", "markdown"):
            result = subprocess.run([*common, "report-assessment", "--file", str(initialized),
                                     "--format", format_value], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        for malformed in (["not an assessment"], {"schema_version": 99}, {"schema_version": 2, "review": []}):
            initialized.write_text(json.dumps(malformed), encoding="utf-8")
            result = subprocess.run([*common, "validate-assessment", "--file", str(initialized)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertNotIn("Traceback", result.stdout + result.stderr)
        initialized.write_text("{", encoding="utf-8")
        result = subprocess.run([*common, "report-assessment", "--file", str(initialized)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
