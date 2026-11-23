"""Behavioral checks for scoped merge decisions and persisted regression requirements."""
import copy
from pathlib import Path
import re
import shutil
import tempfile
import unittest

import review_assessment as review
import test_review_assessment as existing
from toolkit import validate_assessment


class PRReviewTests(unittest.TestCase):
    save = existing.ReviewAssessmentTests.save
    retrieve = existing.ReviewAssessmentTests.retrieve
    decisions = existing.ReviewAssessmentTests.decisions
    check = existing.ReviewAssessmentTests.check
    ready = existing.ReviewAssessmentTests.ready

    def setUp(self):
        existing.ReviewAssessmentTests.setUp(self)
        self.ready()
        check = self.doc["checks"][0]
        check.update(result="pass", result_reason="The current fixture satisfies the intended restriction.",
                     additional=True, coverage_delta="Add a sibling-denial assertion absent from the ordinary fixture suite.")
        test = self.root / "test_regression.py"
        test.write_text("def test_current_restriction():\n    assert True\n", encoding="utf-8")
        self.doc["merge_review"] = {
            "rationale": "The scoped criterion and its additional library-based regression passed on the reviewed revision.",
            "criteria": [{"id": "auth-boundary", "description": "The changed boundary preserves the required restriction.",
                          "check_ids": [check["id"]], "required": True}],
            "findings": [],
            "required_tests": [{"id": "R1", "description": "Retain the sibling-denial regression.", "finding_ids": [],
                                "check_ids": [check["id"]], "status": "passed", "artifact": test.name,
                                "sha256": review.digest(test), "reason": "The check evidence records this fixture's current outcome."}],
        }
        self.save()

    def finding(self, relation="introduced", must_fix=True):
        check = self.doc["checks"][0]
        check.update(result="fail", result_reason="The fixture reproduces the broken restriction.")
        return {"id": "F1", "title": "A synthetic restriction is broken", "severity": "high",
                "change_relation": relation, "impact": "Synthetic validation scenario only.",
                "recommendation": "Repair the restriction and retain its regression.",
                "check_ids": [check["id"]], "must_fix": must_fix,
                "reason": "Compare current evidence with the scoped change before attributing this finding."}

    def decision(self):
        self.save()
        return review.report(self.path)

    def test_approve_requires_evidence_and_additional_library_coverage(self):
        report = self.decision()
        self.assertEqual(report["recommendation"]["status"], "approve")
        self.assertEqual(report["finding_counts"]["introduced"], 0)
        markdown = review.markdown(report)
        self.assertIn("Acceptance recommended within the reviewed scope", markdown)
        self.assertIn("Additional library-derived checks", markdown)
        self.assertIn(self.doc["checks"][0]["coverage_delta"], markdown)
        self.assertIn("test_regression.py", markdown)
        self.assertEqual(report["check_results"]["pass"], 1)

    def test_confirmed_new_finding_blocks_and_retains_failing_test(self):
        self.doc["merge_review"]["findings"] = [self.finding()]
        test = self.doc["merge_review"]["required_tests"][0]
        test.update(status="added", finding_ids=["F1"], reason="Persisted reproducer currently exposes the bug.")
        report = self.decision()
        self.assertEqual(report["recommendation"]["status"], "request_changes")
        self.assertEqual(report["finding_counts"]["introduced"], 1)
        self.assertIn("Changes required before accepting", review.markdown(report))
        self.assertEqual(report["missing_regression_tests"], [])
        self.assertEqual(report["check_results"]["fail"], 1)

    def test_approval_explains_when_no_mandatory_tests_were_identified(self):
        self.doc["merge_review"]["required_tests"] = []
        report = self.decision()
        self.assertEqual(report["recommendation"]["status"], "approve")
        self.assertIn("No additional mandatory regression tests were identified", review.markdown(report))

    def test_new_finding_cannot_be_approved_by_clearing_must_fix(self):
        self.doc["merge_review"]["findings"] = [self.finding(must_fix=False)]
        self.doc["merge_review"]["required_tests"] = []
        self.doc["merge_review"]["criteria"] = []
        report = self.decision()
        self.assertEqual(report["recommendation"]["status"], "request_changes")
        self.assertEqual(report["missing_regression_tests"][0]["finding_id"], "F1")

    def test_missing_regression_is_rendered_with_confirmed_finding(self):
        self.doc["merge_review"]["findings"] = [self.finding()]
        self.doc["merge_review"]["required_tests"] = []
        report = self.decision()
        self.assertEqual(report["recommendation"]["status"], "request_changes")
        self.assertIn("Add and execute a regression test", review.markdown(report))

    def test_explicit_missing_required_test_requests_changes(self):
        test = self.doc["merge_review"]["required_tests"][0]
        test.update(status="missing", artifact="", sha256="", check_ids=[], reason="A required test remains to be added.")
        self.assertEqual(self.decision()["recommendation"]["status"], "request_changes")

    def test_added_test_without_completed_execution_is_incomplete(self):
        test = self.doc["merge_review"]["required_tests"][0]
        test.update(status="added", check_ids=[], reason="The persisted regression awaits an available runtime.")
        self.assertEqual(self.decision()["recommendation"]["status"], "incomplete")

    def test_positive_additional_checks_can_approve_without_new_findings(self):
        self.doc["merge_review"]["required_tests"] = []
        self.assertEqual(self.decision()["recommendation"]["status"], "approve")

    def test_only_ordinary_suite_replay_remains_incomplete(self):
        self.doc["checks"][0].update(additional=False, coverage_delta="")
        report = self.decision()
        self.assertEqual(report["recommendation"]["status"], "incomplete")
        self.assertEqual(report["additional_checks"], [])

    def test_additional_check_must_contribute_to_required_scope(self):
        self.doc["merge_review"]["criteria"][0]["required"] = False
        self.assertEqual(self.decision()["recommendation"]["status"], "incomplete")
        self.doc["merge_review"]["criteria"][0]["required"] = True
        self.doc["checks"][0].update(origin="local_analysis", source_ids=[])
        self.assertEqual(self.decision()["recommendation"]["status"], "incomplete")

    def test_missing_explicit_result_and_unfinished_scope_remain_incomplete(self):
        self.doc["checks"][0].pop("result")
        self.doc["merge_review"]["required_tests"] = []
        self.assertEqual(self.decision()["recommendation"]["status"], "incomplete")
        self.doc["checks"][0].update(result="pass")
        self.doc["merge_review"]["criteria"][0]["check_ids"] = []
        self.assertEqual(self.decision()["recommendation"]["status"], "incomplete")

    def test_legacy_schema2_report_never_implicitly_approves(self):
        self.doc.pop("merge_review")
        self.doc["checks"][0].pop("result")
        self.assertTrue(validate_assessment(self.path)["ok"])
        self.assertEqual(self.decision()["recommendation"]["status"], "incomplete")

    def test_pre_existing_nonblocking_finding_can_be_reported_separately(self):
        old = self.check("old-defect", [], origin="local_analysis")
        old.update(result="fail", result_reason="Existing fixture defect reproduced separately.")
        self.doc["checks"].append(old)
        finding = {"id": "OLD", "title": "Existing defect", "severity": "low", "change_relation": "pre_existing",
                   "impact": "Existing synthetic behavior", "recommendation": "Track separately", "check_ids": [old["id"]],
                   "must_fix": False, "reason": "The reviewed PR did not create or expose this behavior."}
        self.doc["merge_review"]["findings"] = [finding]
        report = self.decision()
        self.assertEqual(report["recommendation"]["status"], "approve")
        self.assertEqual(report["finding_counts"]["introduced"], 0)
        self.assertEqual(report["finding_counts"]["pre_existing"], 1)
        finding["change_relation"] = "unclear"
        self.assertEqual(self.decision()["recommendation"]["status"], "incomplete")

    def test_unclassified_failed_check_prevents_approval(self):
        old = self.check("unclassified", [], origin="local_analysis")
        old.update(result="fail", result_reason="This failure needs review.")
        self.doc["checks"].append(old)
        self.assertEqual(self.decision()["recommendation"]["status"], "incomplete")

    def test_unfinished_check_needs_an_explicit_scope_disposition(self):
        pending = self.check("pending", [], status="not_executed", origin="local_analysis")
        pending.update(result="not_executed", result_reason="An optional deployment runtime is unavailable.")
        self.doc["checks"].append(pending)
        self.assertEqual(self.decision()["recommendation"]["status"], "incomplete")
        self.doc["merge_review"]["criteria"].append({
            "id": "deployment-context", "description": "The deployment runtime is outside this local PR review scope.",
            "check_ids": [pending["id"]], "required": False,
        })
        report = self.decision()
        self.assertEqual(report["recommendation"]["status"], "approve")
        optional = report["criterion_results"][1]
        self.assertFalse(optional["required"])
        self.assertEqual(optional["status"], "incomplete")
        self.assertIn("The deployment runtime is outside", review.markdown(report))

    def test_report_explains_source_hypothesis_adaptation_value_and_conclusion(self):
        self.doc["merge_review"]["library_value"] = "The prior step supplied an additional denial control. Time savings were not measured."
        report = self.decision()
        contribution = report["library_contribution"]
        self.assertEqual(contribution["summary"]["additional_executed_checks"], 1)
        self.assertEqual(contribution["summary"]["used_sources"], 1)
        self.assertEqual(contribution["summary"]["unused_selected_sources"], 2)
        trace = next(source for source in contribution["source_uses"] if source["used"])
        self.assertEqual(trace["source_hypothesis"], "authorization fixture")
        self.assertIsNone(trace["source_observation"])
        self.assertEqual(trace["checks"][0]["hypothesis"], self.doc["checks"][0]["hypothesis"])
        self.assertEqual(trace["checks"][0]["result_reason"], self.doc["checks"][0]["result_reason"])
        self.assertEqual(trace["checks"][0]["evidence"], self.doc["checks"][0]["evidence"])
        markdown = review.markdown(report)
        for expected in ("How the library contributed", "Checked hypotheses",
                         "The prior step supplied an additional denial control", "Basis for the recommendation",
                         self.doc["checks"][0]["result_reason"], "assessment JSON"):
            self.assertIn(expected, markdown)
        self.assertLess(markdown.index("How the library contributed"), markdown.index("Basis for the recommendation"))
        self.assertEqual(markdown.count(self.doc["checks"][0]["hypothesis"]), 1)
        self.assertEqual(report["checks"][0]["status"], "supported")
        self.assertEqual(report["checks"][0]["evidence"], self.doc["checks"][0]["evidence"])
        self.assertEqual(report["criterion_results"][0]["status"], "pass")
        self.doc["merge_review"]["library_value"] = []
        self.save()
        self.assertFalse(validate_assessment(self.path)["ok"])

    def test_pending_source_is_selected_but_not_credited_as_used(self):
        source = review.source_id(self.records[1])
        pending = self.check("pending-library", [source], status="not_executed")
        pending.update(result="not_executed", result_reason="The alternate runtime is outside the required review scope.",
                       additional=True, coverage_delta="A planned sibling check remains unexecuted.")
        self.doc["checks"].append(pending)
        self.doc["merge_review"]["criteria"].append({
            "id": "optional", "description": "Alternate-runtime checks are informational for this local review.",
            "check_ids": [pending["id"]], "required": False,
        })
        report = self.decision()
        summary = report["library_contribution"]["summary"]
        self.assertEqual(summary["used_sources"], 1)
        self.assertEqual(summary["additional_executed_checks"], 1)
        trace = next(source_record for source_record in report["library_contribution"]["source_uses"] if source_record["source_id"] == source)
        self.assertFalse(trace["used"])
        self.assertEqual(trace["checks"][0]["result"], "not_executed")

    def test_library_credit_requires_a_linked_failing_check_for_the_new_finding(self):
        local = self.check("local-finding", [], origin="local_analysis")
        local.update(result="fail", result_reason="Direct code analysis reproduced this synthetic defect.")
        self.doc["checks"].append(local)
        finding = self.finding()
        self.doc["checks"][0].update(result="pass", result_reason="The independent library-derived control passes.")
        finding["check_ids"] = [local["id"], self.doc["checks"][0]["id"]]
        self.doc["merge_review"]["findings"] = [finding]
        report = self.decision()
        self.assertEqual(report["library_contribution"]["summary"]["new_findings_informed"], 0)
        self.assertEqual(report["library_contribution"]["new_findings_informed"], [])
        self.doc["checks"][0].update(result="fail", result_reason="The adapted library check now reproduces the same defect.")
        self.doc["merge_review"]["required_tests"][0].update(status="added", finding_ids=[finding["id"]])
        duplicate = copy.deepcopy(self.doc["checks"][0])
        duplicate["id"] = "second-library-check"
        self.doc["checks"].append(duplicate)
        finding["check_ids"].append(duplicate["id"])
        report = self.decision()
        informed = report["library_contribution"]["new_findings_informed"]
        self.assertEqual(len(informed), 1)
        self.assertEqual(informed[0]["id"], finding["id"])
        self.assertEqual(len(informed[0]["source_ids"]), 1)
        finding["change_relation"] = "pre_existing"
        self.assertEqual(self.decision()["library_contribution"]["summary"]["new_findings_informed"], 0)

    def test_regression_cannot_claim_an_unrelated_findings_coverage(self):
        failure = self.check("actual-defect", [], origin="local_analysis")
        failure.update(result="fail", result_reason="The independent defect reproducer fails.")
        self.doc["checks"].append(failure)
        finding = self.finding()
        self.doc["checks"][0].update(result="pass", result_reason="An unrelated control passes.")
        finding["check_ids"] = [failure["id"]]
        self.doc["merge_review"]["findings"] = [finding]
        self.doc["merge_review"]["required_tests"][0]["finding_ids"] = [finding["id"]]
        self.save()
        self.assertFalse(validate_assessment(self.path)["ok"])
        test = self.doc["merge_review"]["required_tests"][0]
        test.update(status="added", check_ids=[failure["id"]], reason="The real defect reproducer is persisted and failing.")
        self.assertEqual(self.decision()["recommendation"]["status"], "request_changes")

    def test_bad_results_artifacts_references_and_revisions_are_rejected(self):
        original = copy.deepcopy(self.doc)
        for mutation in ("result", "status", "additional", "delta", "artifact", "hash", "test_ref", "criterion_ref", "duplicate", "revision", "unsupported_finding"):
            with self.subTest(mutation=mutation):
                self.doc = copy.deepcopy(original)
                check = self.doc["checks"][0]
                test = self.doc["merge_review"]["required_tests"][0]
                if mutation == "result":
                    check["result"] = "secure"
                elif mutation == "status":
                    check["result"] = "inconclusive"
                elif mutation == "additional":
                    check["additional"] = 1
                elif mutation == "delta":
                    check["coverage_delta"] = ""
                elif mutation == "artifact":
                    test["artifact"] = "absent.py"
                elif mutation == "hash":
                    test["sha256"] = "0" * 64
                elif mutation == "test_ref":
                    test["finding_ids"] = ["unknown"]
                elif mutation == "criterion_ref":
                    self.doc["merge_review"]["criteria"][0]["check_ids"] = ["unknown"]
                elif mutation == "duplicate":
                    self.doc["merge_review"]["criteria"] *= 2
                elif mutation == "revision":
                    check["revision"] = self.base
                else:
                    finding = self.finding()
                    check["result"] = "pass"
                    self.doc["merge_review"]["findings"] = [finding]
                self.save()
                self.assertFalse(validate_assessment(self.path)["ok"])

    def test_report_retains_risk_finding_context_and_portable_evidence(self):
        criterion = self.doc["merge_review"]["criteria"][0]
        criterion.update(risk="A sibling actor could cross the changed restriction.",
                         code_locations=["fixture.py:1"])
        finding = self.finding()
        finding.update(kind="security", preconditions="A sibling actor controls the synthetic object identifier.",
                       reproduction="Run the persisted sibling-denial fixture on this revision.",
                       severity_reason="The fixture demonstrates a cross-actor restriction failure.",
                       code_locations=["fixture.py:1"])
        self.doc["merge_review"]["findings"] = [finding]
        self.doc["merge_review"]["required_tests"][0].update(status="added", finding_ids=[finding["id"]])
        result = self.decision()
        self.assertEqual(result["criterion_results"][0]["risk"], criterion["risk"])
        rendered = review.markdown(result)
        for value in (criterion["risk"], *finding["code_locations"], finding["preconditions"],
                      finding["reproduction"], finding["severity_reason"]):
            self.assertIn(value, rendered)
        links = re.findall(r"\]\(<([^>]+)>\)", rendered)
        self.assertTrue(links)
        self.assertTrue(all(not Path(link).is_absolute() for link in links))
        with tempfile.TemporaryDirectory() as destination:
            moved = Path(destination) / "review"
            shutil.copytree(self.root, moved)
            for link in links:
                self.assertEqual((moved / link).read_bytes(), (self.root / link).read_bytes())

    def test_functional_finding_is_separate_without_losing_merge_block(self):
        finding = self.finding()
        finding["kind"] = "functional"
        self.doc["merge_review"]["findings"] = [finding]
        self.doc["merge_review"]["required_tests"][0].update(status="added", finding_ids=[finding["id"]])
        result = self.decision()
        self.assertEqual(result["recommendation"]["status"], "request_changes")
        self.assertEqual(result["library_contribution"]["summary"]["new_findings_informed"], 0)
        rendered = review.markdown(result)
        self.assertIn("Functional observations", rendered)
        self.assertIn("priority high", rendered)
        self.assertNotIn("## Security findings", rendered)
        finding["kind"] = "security"
        self.assertEqual(self.decision()["library_contribution"]["summary"]["new_findings_informed"], 1)

    def test_invalid_optional_risk_and_finding_context_is_rejected(self):
        self.doc["merge_review"]["findings"] = [self.finding()]
        self.doc["merge_review"]["required_tests"][0].update(status="added", finding_ids=["F1"])
        original = copy.deepcopy(self.doc)
        for section, key, bad in (("criteria", "risk", ""), ("criteria", "code_locations", []),
                                  ("findings", "kind", "unknown"), ("findings", "preconditions", []),
                                  ("findings", "reproduction", ""), ("findings", "severity_reason", 1),
                                  ("findings", "code_locations", [""])):
            with self.subTest(section=section, key=key):
                self.doc = copy.deepcopy(original)
                self.doc["merge_review"][section][0][key] = bad
                self.save()
                self.assertFalse(validate_assessment(self.path)["ok"])


if __name__ == "__main__":
    unittest.main()
