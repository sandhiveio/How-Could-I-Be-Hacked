"""Behavioral checks for offline retrieval, containment and evidence validation."""
import copy
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from corpus import search
from defensive_cases import audit
from toolkit import DEFAULT_LIBRARY, contained, validate_assessment
from validate_steps import validate


class ToolkitTests(unittest.TestCase):
    def test_retrieval_preserves_observation_scope(self):
        hits = search(DEFAULT_LIBRARY, "path traversal symlink containment", 8)
        self.assertTrue(hits)
        for hit in hits:
            if not hit["selected_in_source_case"]:
                self.assertIsNone(hit["historical_observation"])
        step = contained(DEFAULT_LIBRARY, hits[0]["artifact_directory"] + "/step.json")
        self.assertTrue(step.is_file())

    def test_defensive_case_is_searchable_and_has_a_step(self):
        hits = search(DEFAULT_LIBRARY, "transcoder process arguments", 10)
        hit = next(hit for hit in hits if hit["kind"] == "defensive_case"
                   and hit["case_title"] == "Transcoder process arguments")
        path = contained(DEFAULT_LIBRARY, hit["artifact_directory"] + "/step.json")
        step = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(hit["review"], step["review"])
        self.assertEqual(hit["source_observation"], step["source_observation"])
        self.assertIsNone(hit["historical_evaluation"])

    def test_publication_audit_detects_a_missing_case_and_wrong_step_id(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            producer = base / "producer"
            absent_id = "case-" + "a" * 32
            source = producer / "cases" / absent_id
            source.mkdir(parents=True)
            (source / "case.json").write_text('{"kind": "curated_case"}', encoding="utf-8")
            published = base / "published"
            shutil.copytree(DEFAULT_LIBRARY, published)
            with closing(sqlite3.connect(published / "index.sqlite")) as db, db:
                row_id, record = next((row_id, record) for row_id, payload
                                      in db.execute("SELECT rowid, record FROM examples")
                                      if (record := json.loads(payload))["kind"] == "defensive_case")
                record["iteration_id"] = "iteration-9999"
                db.execute("UPDATE examples SET record = ? WHERE rowid = ?",
                           (json.dumps(record), row_id))
            result = audit(published, producer)
            self.assertFalse(result["ok"])
            self.assertEqual(result["missing_cases"], [absent_id])
            self.assertEqual(result["index_gaps"], [record["case_id"]])

    def test_containment(self):
        with self.assertRaises(ValueError):
            contained(DEFAULT_LIBRARY, "../SKILL.md")

    def test_step_evidence_selection_and_backtracking(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / "output.txt").write_text("synthetic validator fixture, not security evidence")
            evaluation = dict(id="c", eligible=True, relevance=.8, feasibility=.8,
                              information_gain=.8, novelty=.2, evidence=0,
                              evidence_files=[], rationale="Synthetic validation fixture")
            step = dict(step_id="s1", parent_step_id=None, branch_id="main", context="Fixture",
                        direction="Test validator", candidates=[dict(id="c", origin="local_analysis", text="Fixture")],
                        evaluations=[evaluation], selected_id="c", observation=dict(candidate_id="c",
                        outcome="inconclusive", summary="Fixture", command="fixture", evidence_files=["output.txt"],
                        remaining_uncertainty=[]))
            second = copy.deepcopy(step)
            second.update(step_id="s2", parent_step_id="s1", branch_id="alternative")
            records = [step, second]
            self.assertEqual(validate(records, base), [])
            bad = copy.deepcopy(records)
            bad[1]["observation"]["candidate_id"] = "unexecuted-sibling"
            self.assertTrue(validate(bad, base))
            bad = copy.deepcopy(records)
            bad[0]["parent_step_id"] = "s2"
            self.assertTrue(validate(bad, base))
            bad = copy.deepcopy(records)
            bad[0]["evaluations"] = []
            self.assertTrue(validate(bad, base))
            (base / "output.txt").unlink()
            self.assertTrue(validate(records, base))


if __name__ == "__main__":
    unittest.main()
