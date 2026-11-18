"""Record offline retrieval and report evidence-backed use in a private review."""
import hashlib
import json
from pathlib import Path
import re
import uuid

from corpus import search
from offline_io import read, write

STATUSES = {"supported", "refuted", "inconclusive", "not_executed"}
COMMIT = re.compile(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})\Z")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(value, where, *, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValueError(f"{where}: expected {'a string' if empty else 'nonempty text'}")
    return value


def array(value, where):
    if not isinstance(value, list):
        raise ValueError(f"{where}: expected an array")
    return value


def object_value(value, where):
    if not isinstance(value, dict):
        raise ValueError(f"{where}: expected an object")
    return value


def string_array(value, where, *, nonempty=False):
    items = array(value, where)
    for item in items:
        text(item, where)
    if nonempty and not items:
        raise ValueError(f"{where}: expected at least one entry")
    if len(set(items)) != len(items):
        raise ValueError(f"{where}: duplicate entry")
    return items


def source_id(record):
    record = object_value(record, "search result")
    candidate = object_value(record.get("candidate"), "search result candidate")
    parts = [record.get("case_id"), record.get("iteration_id"), candidate.get("id")]
    for part in parts:
        text(part, "search result identity")
        if "/" in part:
            raise ValueError("search result identity cannot contain a slash")
    return "/".join(parts)


def scaffold(target, mode, base, head, root, inventory):
    if mode == "pr" and not (COMMIT.fullmatch(base or "") and COMMIT.fullmatch(head or "")):
        raise ValueError("PR mode needs full --base and --head commit IDs")
    result = {
        "schema_version": 2,
        "target": target,
        "scope": "",
        "review": {"mode": mode, "diff_base": base or "", "head": head or "",
                   "tested_revision": head or "", "build_id": ""},
        "library": {"index_sha256": digest(root / "index.sqlite"),
                    "inventory": {key: inventory[key] for key in ("cases", "steps", "search_entries")}},
        "searches": [],
        "decisions": [],
        "checks": [],
        "gaps": [],
        "blockers": [],
    }
    if mode == "pr":
        from pr_review import scaffold as merge_scaffold
        result["merge_review"] = merge_scaffold()
    return result


def record_search(path, root, query, mechanism, limit):
    """One writer per assessment; publish a unique receipt before the atomic journal update."""
    path, root = Path(path).resolve(), Path(root).resolve()
    doc = object_value(read(path), "assessment")
    if doc.get("schema_version") != 2:
        raise ValueError("search-assessment requires a schema_version 2 assessment")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if not query.strip() and not (mechanism or "").strip():
        raise ValueError("Provide --query or --mechanism")
    snapshot = object_value(doc.get("library"), "library")
    searches = array(doc.get("searches"), "searches")
    before = digest(root / "index.sqlite")
    if snapshot.get("index_sha256") != before:
        raise ValueError("Library snapshot changed; start a new assessment for the new snapshot")
    records = search(root, query, limit, mechanism=mechanism)
    if digest(root / "index.sqlite") != before:
        raise ValueError("Library snapshot changed during retrieval; retry from a stable snapshot")
    results = [{**record, "source_id": source_id(record)} for record in records]
    receipt = {"query": query, "mechanism": mechanism, "limit": limit,
               "library_index_sha256": before, "results": results}
    receipt_id = "search-" + uuid.uuid4().hex
    relative = Path(path.stem + "-artifacts") / (receipt_id + ".json")
    output = path.parent / relative
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    searches.append({"id": receipt_id, "query": query, "mechanism": mechanism, "limit": limit,
                     "result_artifact": relative.as_posix(), "sha256": digest(output)})
    write(path, doc)
    return {"search_id": receipt_id, "result_artifact": str(output), "results": results}


def checked_artifact(entry, key, parent, where):
    name = text(entry.get(key), where + "." + key)
    path = (parent / name).resolve()
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"{where}: artifact is missing or empty: {name}")
    if entry.get("sha256") != digest(path):
        raise ValueError(f"{where}: artifact checksum changed: {name}")
    return path


def retrieval_sources(doc, parent):
    snapshot = object_value(doc.get("library"), "library")
    if not re.fullmatch(r"[0-9a-f]{64}", text(snapshot.get("index_sha256"), "library.index_sha256")):
        raise ValueError("library.index_sha256: expected a SHA-256 digest")
    inventory = object_value(snapshot.get("inventory"), "library.inventory")
    for key in ("cases", "steps", "search_entries"):
        value = inventory.get(key)
        if type(value) is not int or value < 0:
            raise ValueError(f"library.inventory.{key}: expected a nonnegative integer")
    sources, seen_ids, seen_artifacts = {}, set(), set()
    for entry in array(doc.get("searches"), "searches"):
        entry = object_value(entry, "searches entry")
        sid = text(entry.get("id"), "search.id")
        if sid in seen_ids:
            raise ValueError("searches: duplicate search ID")
        seen_ids.add(sid)
        query = text(entry.get("query"), "search.query", empty=True)
        mechanism = entry.get("mechanism")
        if mechanism is not None:
            text(mechanism, "search.mechanism")
        if not query.strip() and not mechanism:
            raise ValueError("search needs a query or mechanism")
        limit = entry.get("limit")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("search.limit must be an integer between 1 and 100")
        artifact = checked_artifact(entry, "result_artifact", parent, "search")
        if artifact in seen_artifacts:
            raise ValueError("searches: each search needs its own receipt")
        seen_artifacts.add(artifact)
        receipt = object_value(read(artifact), "search receipt")
        for key in ("query", "mechanism", "limit"):
            if receipt.get(key) != entry.get(key):
                raise ValueError(f"search receipt {key} differs from journal")
        if receipt.get("library_index_sha256") != snapshot["index_sha256"]:
            raise ValueError("search receipt uses a different library snapshot")
        results = array(receipt.get("results"), "search receipt results")
        if len(results) > limit:
            raise ValueError("search receipt exceeds its retrieval limit")
        for record in results:
            identity = source_id(record)
            if record.get("source_id") != identity:
                raise ValueError("search result source_id differs from its identity")
            previous = sources.get(identity)
            # Different queries can rank the same source differently.
            comparable = {key: value for key, value in record.items() if key != "retrieval_score"}
            if previous is not None and comparable != previous:
                raise ValueError("Conflicting records for one source in the same snapshot")
            sources[identity] = comparable
    if len(sources) > inventory["search_entries"]:
        raise ValueError("Retrieved entries exceed the recorded library inventory")
    if len({(record["case_id"], record["iteration_id"]) for record in sources.values()}) > inventory["steps"]:
        raise ValueError("Retrieved steps exceed the recorded library inventory")
    return sources


def validated(path):
    path = Path(path).resolve()
    doc = object_value(read(path), "assessment")
    if doc.get("schema_version") != 2:
        raise ValueError("This report requires schema_version 2")
    for key in ("target", "scope"):
        text(doc.get(key), key)
    review = object_value(doc.get("review"), "review")
    if review.get("mode") not in {"repository", "pr"}:
        raise ValueError("review.mode must be repository or pr")
    for key in ("diff_base", "head", "build_id"):
        text(review.get(key), "review." + key, empty=True)
    revision = text(review.get("tested_revision"), "review.tested_revision")
    if review["mode"] == "pr":
        for key in ("diff_base", "head", "tested_revision"):
            if not COMMIT.fullmatch(review[key]):
                raise ValueError(f"review.{key}: expected a full commit ID")
    sources = retrieval_sources(doc, path.parent)
    decisions = {}
    for entry in array(doc.get("decisions"), "decisions"):
        entry = object_value(entry, "decision")
        sid = text(entry.get("source_id"), "decision.source_id")
        if sid not in sources:
            raise ValueError("Decision references an unknown source")
        if sid in decisions:
            raise ValueError("decisions: duplicate source_id")
        for key in ("applicability", "reason"):
            text(entry.get(key), "decision." + key)
        if type(entry.get("selected")) is not bool:
            raise ValueError("decision.selected must be a boolean")
        decisions[sid] = entry
    checks, check_ids = array(doc.get("checks"), "checks"), set()
    for check in checks:
        check = object_value(check, "check")
        cid = text(check.get("id"), "check.id")
        if cid in check_ids:
            raise ValueError("checks: duplicate check ID")
        check_ids.add(cid)
        for key in ("hypothesis", "adaptation", "test", "expected", "falsifier", "control"):
            text(check.get(key), "check." + key)
        string_array(check.get("code_locations"), "check.code_locations", nonempty=True)
        refs = string_array(check.get("source_ids"), "check.source_ids")
        if check.get("origin") == "library":
            if not refs:
                raise ValueError("Library-derived check needs at least one source")
            if any(sid not in decisions or not decisions[sid]["selected"] for sid in refs):
                raise ValueError("Check source must have a selected decision")
        elif check.get("origin") == "local_analysis":
            if refs:
                raise ValueError("Local-analysis check must have an empty source_ids array")
        else:
            raise ValueError("check.origin must be library or local_analysis")
        if check.get("revision") != revision:
            raise ValueError("check.revision differs from review.tested_revision")
        status = check.get("status")
        if status not in STATUSES:
            raise ValueError("Invalid check status")
        evidence = array(check.get("evidence"), "check.evidence")
        if status == "not_executed":
            if evidence:
                raise ValueError("Unexecuted check cannot have execution evidence")
            text(check.get("reason"), "unexecuted check.reason")
        elif not evidence:
            raise ValueError("Executed check requires actual evidence")
        for entry in evidence:
            entry = object_value(entry, "check evidence")
            for key in ("command", "interpretation"):
                text(entry.get(key), "evidence." + key)
            if type(entry.get("exit_code")) is not int:
                raise ValueError("evidence.exit_code must be an integer")
            checked_artifact(entry, "output_artifact", path.parent, "evidence")
    string_array(doc.get("gaps"), "gaps")
    for blocker in array(doc.get("blockers"), "blockers"):
        blocker = object_value(blocker, "blocker")
        for key in ("description", "owner"):
            text(blocker.get(key), "blocker." + key)
    from pr_review import validate_contract
    validate_contract(doc, path.parent)
    return doc, sources, decisions


def validate(path):
    try:
        validated(path)
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return {"ok": False, "errors": [str(exc)]}
    return {"ok": True, "errors": []}


def report(path):
    doc, sources, decisions = validated(path)
    selected = {sid for sid, item in decisions.items() if item["selected"]}
    executed = [item for item in doc["checks"] if item["status"] != "not_executed"]
    used = {sid for check in executed for sid in check["source_ids"]}

    def steps(identities):
        return len({(sources[sid]["case_id"], sources[sid]["iteration_id"]) for sid in identities})

    counts = {
        "searches": len(doc["searches"]),
        "retrieved_entries": len(sources), "retrieved_steps": steps(sources),
        "considered_entries": len(decisions), "considered_steps": steps(decisions),
        "selected_entries": len(selected), "selected_steps": steps(selected),
        "used_entries": len(used), "used_steps": steps(used),
        "executed_checks": len(executed),
        "pending_checks": len(doc["checks"]) - len(executed),
        "local_analysis_checks": sum(check["origin"] == "local_analysis" for check in executed),
        "outcomes": {status: sum(check["status"] == status for check in doc["checks"])
                     for status in sorted(STATUSES)},
    }
    source_records = [{key: record[key] for key in (
        "source_id", "case_id", "iteration_id", "candidate", "artifact_directory", "title",
        "candidate_role", "historical_observation", "source_observation", "observation_scope") if key in record}
        for record in sources.values()]
    from pr_review import library_contribution, outcome
    return {"schema_version": 2, "assessment_file": str(Path(path).resolve()),
            "target": doc["target"], "scope": doc["scope"],
            "review": doc["review"], "library": doc["library"], "counts": counts,
            "searches": doc["searches"], "sources": source_records,
            "decisions": doc["decisions"], "checks": doc["checks"],
            "gaps": doc["gaps"], "blockers": doc["blockers"], **outcome(doc),
            "library_contribution": library_contribution(doc, sources, decisions)}


def markdown(result):
    def cell(value):
        return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace("\n", " ")

    def artifact_link(name):
        target = (Path(result["assessment_file"]).parent / name).resolve().as_posix()
        label = cell(name).replace("[", "\\[").replace("]", "\\]")
        return f"[{label}](<{target}>)"

    review, counts = result["review"], result["counts"]
    lines = ["# Security review", "", f"Target — {cell(result['target'])}", "",
             f"Scope — {cell(result['scope'])}", "",
             f"Mode — {review['mode']}. Diff base — {cell(review['diff_base']) or 'unspecified'}. "
             f"Reviewed head — {cell(review['head']) or 'unspecified'}. "
             f"Tested revision — {cell(review['tested_revision'])}. Build — {cell(review['build_id']) or 'unspecified'}.",
             "", f"Library index SHA-256 — {result['library']['index_sha256']}", ""]
    recommendation = result["recommendation"]
    labels = {"approve": "PR can be accepted within the reviewed scope", "request_changes": "Changes required before accepting the PR",
              "incomplete": "Review incomplete", "not_applicable": "Repository or module review"}
    lines += ["## Merge recommendation", "", labels[recommendation["status"]], ""]
    lines += ["- " + cell(reason) for reason in recommendation["reasons"]]
    if result["merge_review"]["rationale"]:
        lines += ["", cell(result["merge_review"]["rationale"])]
    lines += ["", "### Basis for the recommendation", "", "| Criterion | Scope | Result | Check observations |",
              "| --- | --- | --- | --- |"]
    for criterion in result["criterion_results"]:
        reasons = " ".join(f"{check['id']} — {check['result']}. {check['reason']}" for check in criterion["checks"])
        values = (criterion["description"], "required" if criterion["required"] else "optional", criterion["status"], reasons)
        lines.append("| " + " | ".join(cell(value) for value in values) + " |")
    contribution = result["library_contribution"]
    summary = contribution["summary"]
    lines += ["", "## How the library contributed", "",
              f"Selected sources — {summary['selected_sources']}. Used sources — {summary['used_sources']}. "
              f"Unused selections — {summary['unused_selected_sources']}.", "",
              f"Additional executed library-derived checks — {summary['additional_executed_checks']}. "
              f"Additional passed checks — {summary['additional_passed_checks']}. "
              f"New or newly exposed findings informed by failing library-derived checks — {summary['new_findings_informed']}.", ""]
    if contribution["reviewer_assessment"]:
        lines += ["Reviewer assessment — " + cell(contribution["reviewer_assessment"]), ""]
    for source in contribution["source_uses"]:
        lines += ["### " + cell(source["title"]), "", "Source — " + cell(source["source_id"]), "",
                  "Original source hypothesis — " + cell(source["source_hypothesis"]), "",
                  "Applicability to this PR — " + cell(source["applicability"]), "",
                  "Selection reason — " + cell(source["selection_reason"]), ""]
        historical = source["source_observation"]
        history_text = (historical["outcome"] + ". " + historical["summary"]) if historical else "No executed observation is recorded for this source candidate."
        lines += ["Historical observation — " + cell(history_text), "",
                  "Historical scope — " + cell(source["source_observation_scope"]), ""]
        for check in source["checks"]:
            lines += ["Current hypothesis — " + cell(check["hypothesis"]), "",
                      "Source contribution — " + cell(check["adaptation"]), "",
                      "Additional coverage — " + cell(check["coverage_delta"] or "No additional-coverage claim recorded."), "",
                      "Current test — " + cell(check["test"]), "",
                      f"Hypothesis status — {check['status']}. Safety result — {check['result']}. " + cell(check["result_reason"]), ""]
            for evidence in check["evidence"]:
                lines += ["Observed evidence — " + cell(evidence["interpretation"]) + " " + artifact_link(evidence["output_artifact"]), ""]
    lines += ["", "Finding counts — " + ", ".join(f"{relation} {count}" for relation, count in result["finding_counts"].items()) + ".",
              "", "Check results — " + ", ".join(f"{state} {count}" for state, count in result["check_results"].items()) + ".", "",
              "## Additional library-derived checks", "", "| Check | Additional coverage | How checked | Result |", "| --- | --- | --- | --- |"]
    for check in result["additional_checks"]:
        values = (check["id"], check["coverage_delta"], check["test"], check.get("result", "not_assessed"))
        lines.append("| " + " | ".join(cell(value) for value in values) + " |")
    lines += ["", "## Findings", ""]
    for finding in result["merge_review"]["findings"]:
        lines += [f"### {cell(finding['id'])} — {cell(finding['title'])}", "",
                  f"Severity — {finding['severity']}. Change relation — {finding['change_relation']}. Must fix — {finding['must_fix']}.", "",
                  f"Impact — {cell(finding['impact'])}", "", f"Recommendation — {cell(finding['recommendation'])}", "",
                  f"Evidence checks — {cell(', '.join(finding['check_ids']))}. {cell(finding['reason'])}", ""]
    lines += ["## Required regression tests", "", "| Test | Requirement | State | Artifact | Checks |", "| --- | --- | --- | --- | --- |"]
    for test in result["merge_review"]["required_tests"]:
        artifact = artifact_link(test["artifact"]) if test["artifact"] else "pending"
        description = test["description"] + " " + test["reason"]
        if test["finding_ids"]:
            description += " Findings — " + ", ".join(test["finding_ids"]) + "."
        values = (test["id"], description, test["status"])
        lines.append("| " + " | ".join(cell(value) for value in values) + f" | {artifact} | {cell(', '.join(test['check_ids']))} |")
    for missing in result["missing_regression_tests"]:
        lines.append(f"| {cell(missing['finding_id'])} | {cell(missing['description'])} | missing | pending | |")
    lines += [""]
    inventory = result["library"]["inventory"]
    lines += [f"Library inventory — {inventory['steps']} steps, {inventory['search_entries']} search entries.",
              "", "| Stage | Unique entries | Unique steps |", "| --- | ---: | ---: |"]
    for stage in ("retrieved", "considered", "selected", "used"):
        lines.append(f"| {stage.capitalize()} | {counts[stage + '_entries']} | {counts[stage + '_steps']} |")
    lines += ["", f"Executed checks — {counts['executed_checks']}. Pending checks — {counts['pending_checks']}. "
              f"Executed checks from local analysis — {counts['local_analysis_checks']}.",
              "", "Current hypothesis outcomes — " + ", ".join(
                  f"{status} {number}" for status, number in counts["outcomes"].items()) + ".",
              "", "Counts describe saved retrieval and execution records. Review coverage depends on the checks and gaps below.",
              "", "| Check | Sources | Adaptation | Current outcome | Evidence |",
              "| --- | --- | --- | --- | --- |"]
    for check in result["checks"]:
        evidence = ", ".join(artifact_link(entry["output_artifact"]) for entry in check["evidence"])
        outcome = check["status"]
        if outcome == "not_executed":
            outcome += " — " + check["reason"]
        if "result" in check:
            outcome = check["result"] + " — " + check["result_reason"]
        values = [check["id"], ", ".join(check["source_ids"]) or "local analysis", check["adaptation"], outcome]
        lines.append("| " + " | ".join(cell(value) for value in values) + f" | {evidence} |")
    lines += ["", "## Check evidence", ""]
    for check in result["checks"]:
        lines += [f"### {cell(check['id'])}", "",
                  f"Hypothesis — {cell(check['hypothesis'])}", "",
                  f"Hypothesis status — {check['status']}. Safety result — {check.get('result', 'not_assessed')}. " + cell(check.get("result_reason", "")), "",
                  f"Code — {cell(', '.join(check['code_locations']))}. Revision — {cell(check['revision'])}.", "",
                  f"Test — {cell(check['test'])}", "",
                  f"Expected supporting result — {cell(check['expected'])}", "",
                  f"Falsifier — {cell(check['falsifier'])}", "",
                  f"Control — {cell(check['control'])}", ""]
        for evidence in check["evidence"]:
            lines += ["Command", "", *["    " + line for line in evidence["command"].splitlines()], "",
                      f"Exit code — {evidence['exit_code']}. Output — {artifact_link(evidence['output_artifact'])}.", "",
                      f"Interpretation — {cell(evidence['interpretation'])}", ""]
    lines += ["## Retrieval receipts", ""]
    for entry in result["searches"]:
        lines.append(f"- {cell(entry['id'])}. Query — {cell(entry['query']) or '(tag only)'}. "
                     f"Mechanism — {cell(entry['mechanism'] or 'any')}. Limit — {entry['limit']}. "
                     f"Receipt — {artifact_link(entry['result_artifact'])}.")
    lines += ["", "## Source decisions", ""]
    for entry in result["decisions"]:
        state = "selected" if entry["selected"] else "set aside"
        lines.append(f"- {cell(entry['source_id'])} — {state}. {cell(entry['applicability'])} {cell(entry['reason'])}")
    lines += ["", "## Unchecked areas", ""]
    lines += ["- " + cell(gap) for gap in result["gaps"]] or ["- No gaps recorded."]
    lines += ["", "## Blockers", ""]
    lines += [f"- {cell(item['description'])} — owner {cell(item['owner'])}." for item in result["blockers"]] or ["- No blockers recorded."]
    lines += ["", "Supported and refuted refer to each current hypothesis. Source-case observations remain historical context.",
              "Validation checks record consistency and artifacts. The reviewer assesses the meaning and adequacy of the evidence."]
    return "\n".join(lines) + "\n"
