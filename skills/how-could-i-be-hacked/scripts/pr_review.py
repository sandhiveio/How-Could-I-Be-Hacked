"""Validate and derive a scoped PR recommendation from current checks and regressions."""

from review_assessment import array, checked_artifact, object_value, string_array, text

RESULTS = {"pass", "fail", "inconclusive", "not_executed"}
RELATIONS = {"introduced", "exposed_by_change", "pre_existing", "unclear"}
NEW_RELATIONS = {"introduced", "exposed_by_change"}


def scaffold():
    return {"rationale": "", "library_value": "", "criteria": [], "findings": [], "required_tests": []}


def records(value, label):
    result = {}
    for item in array(value, label):
        item = object_value(item, label + " entry")
        identity = text(item.get("id"), label + ".id")
        if identity in result:
            raise ValueError(label + ": duplicate id")
        result[identity] = item
    return result


def references(value, available, label, *, nonempty=False):
    identities = string_array(value, label, nonempty=nonempty)
    if any(identity not in available for identity in identities):
        raise ValueError(label + ": unknown reference")
    return identities


def validate_contract(doc, parent):
    checks = {check["id"]: check for check in doc["checks"]}
    for check in checks.values():
        if "result" in check:
            result = check["result"]
            if result not in RESULTS:
                raise ValueError("check.result must be pass, fail, inconclusive, or not_executed")
            text(check.get("result_reason"), "check.result_reason")
            if result in {"pass", "fail"} and check["status"] in {"inconclusive", "not_executed"}:
                raise ValueError("A pass/fail result needs a completed, conclusive check")
            if result in {"inconclusive", "not_executed"} and check["status"] != result:
                raise ValueError("check.result and hypothesis status disagree about execution")
        if "additional" in check and type(check["additional"]) is not bool:
            raise ValueError("check.additional must be a boolean")
        if check.get("additional"):
            text(check.get("coverage_delta"), "check.coverage_delta")
    if "merge_review" not in doc:
        return
    if doc["review"]["mode"] != "pr":
        raise ValueError("merge_review requires PR mode")
    contract = object_value(doc["merge_review"], "merge_review")
    text(contract.get("rationale"), "merge_review.rationale", empty=True)
    if "library_value" in contract:
        text(contract["library_value"], "merge_review.library_value", empty=True)
    criteria = records(contract.get("criteria"), "criteria")
    for criterion in criteria.values():
        text(criterion.get("description"), "criterion.description")
        if "risk" in criterion:
            text(criterion["risk"], "criterion.risk")
        if "code_locations" in criterion:
            string_array(criterion["code_locations"], "criterion.code_locations", nonempty=True)
        references(criterion.get("check_ids"), checks, "criterion.check_ids")
        if type(criterion.get("required")) is not bool:
            raise ValueError("criterion.required must be a boolean")
    findings = records(contract.get("findings"), "findings")
    for finding in findings.values():
        for key in ("title", "impact", "recommendation", "reason"):
            text(finding.get(key), "finding." + key)
        if finding.get("kind", "security") not in {"security", "functional"}:
            raise ValueError("finding.kind must be security or functional")
        for key in ("preconditions", "reproduction", "severity_reason"):
            if key in finding:
                text(finding[key], "finding." + key)
        if "code_locations" in finding:
            string_array(finding["code_locations"], "finding.code_locations", nonempty=True)
        if finding.get("severity") not in {"critical", "high", "medium", "low"}:
            raise ValueError("Invalid finding severity")
        if finding.get("change_relation") not in RELATIONS:
            raise ValueError("Invalid finding change_relation")
        if type(finding.get("must_fix")) is not bool:
            raise ValueError("finding.must_fix must be a boolean")
        refs = references(finding.get("check_ids"), checks, "finding.check_ids", nonempty=True)
        if not any(checks[identity].get("result") == "fail" and checks[identity]["evidence"] for identity in refs):
            raise ValueError("A confirmed finding needs current executed fail-result evidence")
    tests = records(contract.get("required_tests"), "required_tests")
    for test in tests.values():
        text(test.get("description"), "required_test.description")
        text(test.get("reason"), "required_test.reason")
        finding_refs = references(test.get("finding_ids"), findings, "required_test.finding_ids")
        refs = references(test.get("check_ids"), checks, "required_test.check_ids")
        status = test.get("status")
        if status not in {"missing", "added", "passed"}:
            raise ValueError("Invalid required test status")
        if status == "missing":
            for key in ("artifact", "sha256"):
                text(test.get(key), "required_test." + key, empty=True)
            if test["artifact"] or test["sha256"]:
                raise ValueError("A missing required test must have empty artifact and sha256")
            continue
        checked_artifact(test, "artifact", parent, "required test")
        executed_refs = {identity for identity in refs if checks[identity]["status"] != "not_executed"}
        if executed_refs and any(not executed_refs.intersection(findings[identity]["check_ids"]) for identity in finding_refs):
            raise ValueError("A finding-linked regression test must reference that finding's evidence checks")
        if status == "passed" and (not refs or any(checks[identity].get("result") != "pass" for identity in refs)):
            raise ValueError("A passed required test needs current pass-result checks")


def outcome(doc):
    checks = {check["id"]: check for check in doc["checks"]}
    check_results = {result: sum(check.get("result") == result for check in checks.values()) for result in sorted(RESULTS)}
    check_results["not_assessed"] = sum("result" not in check for check in checks.values())
    additional = [check for check in checks.values() if check.get("additional") and check["origin"] == "library"]
    contract = doc.get("merge_review", scaffold())
    findings, tests = contract["findings"], contract["required_tests"]
    finding_counts = {relation: sum(finding["change_relation"] == relation for finding in findings) for relation in sorted(RELATIONS)}
    missing_tests = []
    blocking, incomplete = [], []
    for finding in findings:
        identity = finding["id"]
        if finding["change_relation"] in NEW_RELATIONS or finding["must_fix"]:
            blocking.append(f"Finding {identity} requires a fix before merge: {finding['title']}")
            if not any(identity in test["finding_ids"] for test in tests):
                missing_tests.append({"finding_id": identity, "description": "Add and execute a regression test for this finding."})
                blocking.append(f"Finding {identity} has no required regression test recorded.")
        elif finding["change_relation"] == "unclear":
            incomplete.append(f"Finding {identity} still needs change attribution.")
    for blocker in doc["blockers"]:
        blocking.append(f"Blocker: {blocker['description']} (owner {blocker['owner']}).")
    for test in tests:
        if test["status"] == "missing":
            blocking.append(f"Required test {test['id']} must be added: {test['description']}")
        elif test["status"] == "added":
            if any(checks[identity].get("result") == "fail" for identity in test["check_ids"]):
                blocking.append(f"Required test {test['id']} still fails: {test['description']}")
            else:
                incomplete.append(f"Required test {test['id']} has been added and still needs a completed passing run: {test['reason']}")
    required = [criterion for criterion in contract["criteria"] if criterion["required"]]
    required_checks = {identity for criterion in required for identity in criterion["check_ids"]}
    scoped_checks = {identity for criterion in contract["criteria"] for identity in criterion["check_ids"]}
    for criterion in required:
        if not criterion["check_ids"]:
            incomplete.append(f"Required criterion {criterion['id']} has no checks recorded.")
        for identity in criterion["check_ids"]:
            result = checks[identity].get("result")
            if result == "fail":
                blocking.append(f"Required criterion {criterion['id']} failed in check {identity}: {checks[identity]['result_reason']}")
            elif result != "pass":
                incomplete.append(f"Required criterion {criterion['id']} is unresolved in check {identity}.")
    classified = {identity for finding in findings for identity in finding["check_ids"]}
    for identity, check in checks.items():
        if check.get("result") != "pass" and identity not in classified and identity not in scoped_checks:
            incomplete.append(f"Unresolved check {identity} needs classification in the review scope or a finding.")
    if not required:
        incomplete.append("Define the required criteria for the reviewed PR scope.")
    if not contract["rationale"].strip():
        incomplete.append("Record the evidence-based rationale for the merge recommendation.")
    qualified = [check for check in additional if check["id"] in required_checks and check.get("result") == "pass"]
    if not qualified:
        incomplete.append("Execute an additional library-derived check tied to a required criterion and describe its coverage delta.")
    if doc["review"]["mode"] != "pr":
        recommendation = {"status": "not_applicable", "reasons": ["This assessment reviews a repository or module."]}
    elif blocking:
        recommendation = {"status": "request_changes", "reasons": list(dict.fromkeys(blocking + incomplete))}
    elif incomplete:
        recommendation = {"status": "incomplete", "reasons": list(dict.fromkeys(incomplete))}
    else:
        reasons = [f"Required criterion {criterion['id']} passed: {criterion['description']}" for criterion in required]
        if tests:
            reasons.append(f"All {len(tests)} recorded required regression tests passed for the tested revision.")
        else:
            reasons.append("No additional mandatory regression tests were identified for this scoped review.")
        reasons.append("Additional library-derived checks passed with recorded adaptations and evidence.")
        recommendation = {"status": "approve", "reasons": reasons}
    return {"recommendation": recommendation, "merge_review": contract, "finding_counts": finding_counts,
            "check_results": check_results, "additional_checks": additional, "missing_regression_tests": missing_tests,
            "criterion_results": criterion_results(contract, checks)}


def criterion_results(contract, checks):
    results = []
    for criterion in contract["criteria"]:
        current = [{"id": identity, "hypothesis": checks[identity]["hypothesis"],
                    "hypothesis_status": checks[identity]["status"],
                    "result": checks[identity].get("result", "not_assessed"),
                    "reason": checks[identity].get("result_reason", checks[identity].get("reason", "Safety result not assessed."))}
                   for identity in criterion["check_ids"]]
        status = "incomplete"
        if any(check["result"] == "fail" for check in current):
            status = "fail"
        elif current and all(check["result"] == "pass" for check in current):
            status = "pass"
        results.append({"id": criterion["id"], "description": criterion["description"],
                        **{key: criterion[key] for key in ("risk", "code_locations") if key in criterion},
                        "required": criterion["required"], "status": status, "checks": current})
    return results


def library_contribution(doc, sources, decisions):
    selected = {identity for identity, decision in decisions.items() if decision["selected"]}
    executed = [check for check in doc["checks"] if check["origin"] == "library" and check["status"] != "not_executed"]
    used = {identity for check in executed for identity in check["source_ids"]}
    additional = [check for check in executed if check.get("additional")]
    failed = {check["id"]: check for check in executed if check.get("result") == "fail"}
    informed = []
    for finding in doc.get("merge_review", scaffold())["findings"]:
        relevant = [identity for identity in finding["check_ids"] if identity in failed]
        if finding.get("kind", "security") == "security" and finding["change_relation"] in NEW_RELATIONS and relevant:
            informed.append({"id": finding["id"], "title": finding["title"], "check_ids": relevant,
                             "source_ids": sorted({identity for check_id in relevant for identity in failed[check_id]["source_ids"]})})
    traces = []
    for identity in sorted(selected):
        source, decision = sources[identity], decisions[identity]
        source_checks = []
        for check in doc["checks"]:
            if identity not in check["source_ids"]:
                continue
            source_checks.append({key: check[key] for key in ("id", "hypothesis", "adaptation", "test", "status", "evidence")})
            source_checks[-1].update(result=check.get("result", "not_assessed"),
                                    result_reason=check.get("result_reason", check.get("reason", "Safety result not assessed.")),
                                    additional=check.get("additional", False), coverage_delta=check.get("coverage_delta", ""))
        traces.append({"source_id": identity,
                       "title": source.get("title") or source.get("case_title") or source.get("surface", "Security investigation step").split(". ", 1)[0],
                       "source_hypothesis": source.get("review", {}).get("invariant", source["candidate"]["text"]),
                       "source_observation": source.get("source_observation") or source.get("historical_observation"),
                       "source_observation_scope": source.get("observation_scope", "Source case only. Retest on the current code."),
                       "applicability": decision["applicability"], "selection_reason": decision["reason"],
                       "used": identity in used, "checks": source_checks})
    return {"reviewer_assessment": doc.get("merge_review", {}).get("library_value", ""),
            "summary": {"selected_sources": len(selected), "used_sources": len(used),
                        "unused_selected_sources": len(selected - used),
                        "additional_executed_checks": len(additional),
                        "additional_passed_checks": sum(check.get("result") == "pass" for check in additional),
                        "new_findings_informed": len(informed)},
            "source_uses": traces, "new_findings_informed": informed}
