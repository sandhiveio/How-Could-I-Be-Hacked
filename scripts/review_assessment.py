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

    def artifact_link(name, label=None):
        target = (Path(result["assessment_file"]).parent / name).resolve().as_posix()
        display = cell(label or Path(name).name).replace("[", "\\[").replace("]", "\\]")
        return f"[{display}](<{target}>)"

    review = result["review"]
    counts = result["counts"]
    recommendation = result["recommendation"]
    contribution = result["library_contribution"]
    summary = contribution["summary"]
    inventory = result["library"]["inventory"]
    labels = {"approve": "PR can be accepted within the reviewed scope",
              "request_changes": "Changes required before accepting the PR",
              "incomplete": "Review incomplete", "not_applicable": "Repository or module review"}
    lines = ["# Security review", "", "**" + labels[recommendation["status"]] + "**", "",
             "Tested revision — " + cell(review["tested_revision"]), "",
             "## How the library contributed", "",
             f"Library — {inventory['steps']} steps, {inventory['search_entries']} entries. Searches — {counts['searches']}.", "",
             "Unique entries / steps — " + ", ".join(
                 f"{stage} {counts[stage + '_entries']}/{counts[stage + '_steps']}"
                 for stage in ("retrieved", "considered", "selected", "used")) + ".", "",
             f"Additional library-derived checks — {summary['additional_executed_checks']} executed, "
             f"{summary['additional_passed_checks']} passed. New findings informed — {summary['new_findings_informed']}.", ""]
    if contribution["reviewer_assessment"]:
        lines += [cell(contribution["reviewer_assessment"]), ""]
    lines += ["## Checked hypotheses", "",
              "| Hypothesis | Library contribution | How checked | Observed result / evidence |",
              "| --- | --- | --- | --- |"]
    for check in result["checks"]:
        if check["origin"] == "local_analysis":
            added = "Local analysis"
        elif check.get("additional"):
            added = check["coverage_delta"]
        else:
            added = "Library-guided existing check"
        status = check.get("result", "hypothesis " + check["status"])
        explanation = check.get("result_reason", check.get("reason", ""))
        if not explanation:
            explanation = " ".join(entry["interpretation"] for entry in check["evidence"])
        links = " ".join(artifact_link(entry["output_artifact"]) for entry in check["evidence"])
        values = (check["id"] + " — " + check["hypothesis"], added, check["test"])
        outcome = cell(status + ". " + explanation)
        lines.append("| " + " | ".join(cell(value) for value in values) + f" | {outcome} {links} |")
    lines += ["", "## Basis for the recommendation", ""]
    rationale = result["merge_review"]["rationale"]
    if rationale:
        lines += [cell(rationale), ""]
    if recommendation["status"] != "approve" or not rationale:
        lines += ["- " + cell(reason) for reason in recommendation["reasons"]]
    for criterion in result["criterion_results"]:
        if not criterion["required"]:
            lines += ["- Optional scope — " + cell(criterion["description"]) + f" ({criterion['status']})."]
    if result["merge_review"]["findings"]:
        lines += ["", "## Findings and required fixes", "",
                  "| Finding / impact | Relation | Required action | Checks |",
                  "| --- | --- | --- | --- |"]
        for finding in result["merge_review"]["findings"]:
            values = (finding["severity"] + " — " + finding["title"] + ". " + finding["impact"],
                      finding["change_relation"], finding["recommendation"], ", ".join(finding["check_ids"]))
            lines.append("| " + " | ".join(cell(value) for value in values) + " |")
    tests = result["merge_review"]["required_tests"]
    if tests or result["missing_regression_tests"]:
        lines += ["", "## Required regression tests", "",
                  "| Test | State | Artifact |", "| --- | --- | --- |"]
        for test in tests:
            description = test["id"] + " — " + test["description"]
            if test["status"] != "passed":
                description += " " + test["reason"]
            artifact = artifact_link(test["artifact"]) if test["artifact"] else "pending"
            lines.append(f"| {cell(description)} | {test['status']} | {artifact} |")
        for missing in result["missing_regression_tests"]:
            lines.append(f"| {cell(missing['finding_id'] + ' — ' + missing['description'])} | missing | pending |")
    elif recommendation["status"] == "approve":
        lines += ["", "No additional mandatory regression tests were identified for this scoped review."]
    if result["blockers"]:
        lines += ["", "## Blockers", ""]
        lines += [f"- {cell(item['description'])} — owner {cell(item['owner'])}." for item in result["blockers"]]
    if result["gaps"]:
        lines += ["", "## Review limits", ""]
        lines += ["- " + cell(gap) for gap in result["gaps"]]
    lines += ["", "## Scope and evidence", "", cell(result["scope"]), "",
              f"Diff base — {cell(review['diff_base']) or 'unspecified'}. Reviewed head — {cell(review['head']) or 'unspecified'}.", "",
              "Build — " + cell(review["build_id"] or "unspecified") + ".", "",
              "Full hypotheses, source decisions, controls, commands and evidence — "
              + artifact_link(result["assessment_file"], "assessment JSON") + ".", ""]
    if result["searches"]:
        lines += ["Search receipts — " + ", ".join(
            artifact_link(entry["result_artifact"], entry["query"] or entry["mechanism"])
            for entry in result["searches"]) + ".", ""]
    return "\n".join(lines) + "\n"
