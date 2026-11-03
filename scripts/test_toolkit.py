"""Behavioral checks for offline retrieval, containment and evidence validation."""
import copy
from pathlib import Path
import tempfile
import unittest
from corpus import search
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
