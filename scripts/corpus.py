#!/usr/bin/env python3
"""Bake curated anonymous case trajectories; search the resulting library offline."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import uuid

from offline_io import read, write

CASE_KEYS = {"kind", "hint", "surface", "assumptions", "plans", "selected_plan_id", "iterations"}
ROUND_KEYS = {"hint_before", "candidates", "evaluations", "selected_id", "observation"}
OBSERVATION_KEYS = {"outcome", "summary", "next_hint"}
LINEAGE_KEYS = {"step_id", "parent_step_id", "branch_id"}


def steps(case):
    """Resolve chronological records into an acyclic tree; accept legacy linear input."""
    seen = {}
    previous = None
    for n, step in enumerate(case["iterations"], 1):
        sid = step.get("step_id", f"iteration-{n:04d}")
        text(sid, "step_id")
        if sid in seen:
            raise ValueError("step_id must be unique")
        pid = step.get("parent_step_id", previous)
        if pid is not None and (not isinstance(pid, str) or pid not in seen):
            raise ValueError("parent_step_id must name an earlier step or be null for the initial plan")
        branch = step.get("branch_id", "main")
        text(branch, "branch_id")
        parent = case["selected_plan_id"] if pid is None else seen[pid]
        yield step, sid, pid, branch, parent
        seen[sid] = step["selected_id"]
        previous = sid
IDENTIFIERS = re.compile(
    r"https?://\S+|\bCVE-\d{4}-\d+\b|\bGHSA-[\w-]+\b|"
    r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|\b(?:\d{1,3}\.){3}\d{1,3}\b|"
    r"[A-Za-z]:[\\/]|/(?:home|Users|workspace|workdir)/\S+|\b[0-9a-f]{40,64}\b|"
    r"\b(?:Bearer\s+\S+|sk-(?:proj-|or-|live-)?[\w-]{12,})", re.IGNORECASE)


def shape(obj, allowed, required, where):
    if not isinstance(obj, dict) or set(obj) - allowed or required - set(obj):
        raise ValueError(f"Unexpected or missing fields at {where}; use the curated allowlisted schema")


def text(value, where):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Nonempty text required at {where}")


def scan(value, denied, where="case"):
    if isinstance(value, str):
        if IDENTIFIERS.search(value) or any(term.casefold() in value.casefold() for term in denied):
            raise ValueError(f"Source identifier found at {where}; generalize it before baking")
    elif isinstance(value, dict):
        for key, item in value.items():
            scan(item, denied, f"{where}.{key}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            scan(item, denied, f"{where}[{i}]")


def validate(case, denied=()):
    shape(case, CASE_KEYS, CASE_KEYS, "case")
    if case["kind"] not in ("curated_case", "synthetic_example"):
        raise ValueError("kind must distinguish a real curated case from a synthetic example")
    text(case["hint"], "hint"); text(case["surface"], "surface")
    for key, minimum in (("assumptions", 1), ("plans", 3)):
        if not isinstance(case[key], list) or len(case[key]) < minimum:
            raise ValueError(f"{key} needs at least {minimum} entries")
        for entry in case[key]:
            text(entry, key)
    if not isinstance(case["iterations"], list) or len(case["iterations"]) < 2:
        raise ValueError("A case must preserve at least two actual iterations")
    known = {f"plan-{i+1}" for i in range(len(case["plans"]))}
    parent = case["selected_plan_id"]
    if not isinstance(parent, str) or parent not in known:
        raise ValueError("selected_plan_id must identify an initial plan")
    for step, sid, pid, branch, parent in steps(case):
        shape(step, ROUND_KEYS | LINEAGE_KEYS, ROUND_KEYS, f"step {sid}")
        text(step["hint_before"], "hint_before")
        if not isinstance(step["candidates"], list):
            raise ValueError("candidates must be an array of valid curated hypotheses")
        ids = set()
        for candidate in step["candidates"]:
            shape(candidate, {"id", "text", "parent_id"}, {"id", "text", "parent_id"}, "candidate")
            for key in ("id", "text", "parent_id"):
                text(candidate[key], key)
            if candidate["id"] in known or candidate["id"] in ids:
                raise ValueError("Candidate IDs must be unique across the trajectory")
            if candidate["parent_id"] != parent:
                raise ValueError("Candidates must derive from the declared parent step's selection")
            ids.add(candidate["id"])
        if not isinstance(step["evaluations"], list):
            raise ValueError("evaluations must be an array")
        evaluated = set()
        for evaluation in step["evaluations"]:
            shape(evaluation, {"id", "eligible", "score", "rationale"},
                  {"id", "eligible", "score", "rationale"}, "evaluation")
            cid = evaluation["id"]
            if cid in evaluated or cid not in ids | {parent}:
                raise ValueError("Duplicate or unknown evaluated candidate")
            if not isinstance(evaluation["eligible"], bool):
                raise ValueError("eligible must be boolean")
            score = evaluation["score"]
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
                raise ValueError("score must be between 0 and 1")
            text(evaluation["rationale"], "rationale")
            evaluated.add(cid)
        if evaluated != ids | {parent}:
            raise ValueError("Evaluate every retained candidate and the incumbent")
        selected = step["selected_id"]
        if not any(e["id"] == selected and e["eligible"] for e in step["evaluations"]):
            raise ValueError("Selection needs an eligible evaluation")
        shape(step["observation"], OBSERVATION_KEYS, OBSERVATION_KEYS, "observation")
        obs = step["observation"]
        if obs["outcome"] not in ("supported", "refuted", "inconclusive", "not_executed"):
            raise ValueError("Invalid observation outcome")
        if case["kind"] == "curated_case" and obs["outcome"] == "not_executed":
            raise ValueError("Real curated iterations need actual observations")
        text(obs["summary"], "summary"); text(obs["next_hint"], "next_hint")
        parent = selected
        known |= ids
    scan(case, denied)


def bake(case_path, library, denied=()):
    case = read(case_path)
    validate(case, denied)
    root = Path(library)
    root.mkdir(parents=True, exist_ok=True)
    case_id = "case-" + uuid.uuid4().hex
    target = root / "cases" / case_id
    artifacts = []

    def artifact(relative, payload):
        path = target / relative
        write(path, payload)
        artifacts.append({"path": path.relative_to(target).as_posix(),
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})

    artifact("case.json", {"id": case_id, **{k: case[k] for k in ("kind", "hint", "surface", "assumptions")}})
    artifact("planning.json", {"plans": case["plans"], "selected_id": case["selected_plan_id"]})
    previous = None
    parent = case["selected_plan_id"]
    proposals = {f"plan-{i+1}": p for i, p in enumerate(case["plans"])}
    records = []
    for n, (step, iteration_id, previous, branch, parent) in enumerate(steps(case), 1):
        folder = f"iterations/{n:04d}"
        incumbent = {"id": parent, "text": proposals[parent]}
        proposals.update({c["id"]: c["text"] for c in step["candidates"]})
        artifact(folder + "/context.json", {"case_id": case_id, "iteration_id": iteration_id,
                 "previous_iteration_id": previous, "incumbent": incumbent, "hint": step["hint_before"]})
        artifact(folder + "/generation.json", {"candidates": step["candidates"]})
        artifact(folder + "/evaluation.json", {"evaluations": step["evaluations"]})
        artifact(folder + "/selection.json", {"selected_id": step["selected_id"],
                 "selected_text": proposals[step["selected_id"]]})
        artifact(folder + "/observation.json", step["observation"])
        # Retrieval units are independently interpretable. Lineage is supplementary;
        # no external case file or previous step is needed to understand this capsule.
        capsule = {"schema_version": 1, "kind": case["kind"],
                   "context": {"hint": step["hint_before"], "surface": case["surface"],
                               "assumptions": case["assumptions"]},
                   "incumbent": incumbent, "candidates": step["candidates"], "evaluations": step["evaluations"],
                   "selected_id": step["selected_id"], "observation": step["observation"],
                   "lineage": {"case_id": case_id, "iteration_id": iteration_id,
                               "previous_iteration_id": previous, "step_id": iteration_id,
                               "parent_step_id": previous, "branch_id": branch}}
        artifact(folder + "/step.json", capsule)
        evaluations = {e["id"]: e for e in step["evaluations"]}
        for candidate in [*step["candidates"], incumbent]:
            records.append({"case_id": case_id, "iteration_id": iteration_id,
                "kind": case["kind"], "hint": step["hint_before"], "surface": case["surface"],
                "assumptions": case["assumptions"], "candidate": candidate,
                "candidate_role": "incumbent" if candidate["id"] == parent else "generated",
                "historical_evaluation": evaluations[candidate["id"]],
                "historical_observation": step["observation"] if candidate["id"] == step["selected_id"] else None,
                "observation_scope": "source case only; retest applicability on the new target",
                "selected_in_source_case": candidate["id"] == step["selected_id"],
                "parent_step_id": previous, "branch_id": branch,
                "artifact_directory": f"cases/{case_id}/{folder}"})
        previous, parent = iteration_id, step["selected_id"]
    artifact("manifest.json", {"schema_version": 1, "case_id": case_id,
             "iterations": len(case["iterations"]), "artifacts": list(artifacts)})
    # Derived local index contains only reviewed fields, never raw prompts/logs/source paths.
    with closing(sqlite3.connect(root / "index.sqlite")) as db:
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS examples USING fts5(search_text, record UNINDEXED)")
        for record in records:
            searchable = " ".join([record["hint"], record["surface"], *record["assumptions"], record["candidate"]["text"]])
            db.execute("INSERT INTO examples(search_text, record) VALUES (?, ?)",
                       (searchable, json.dumps(record, ensure_ascii=False)))
        db.commit()
    return {"case_id": case_id, "iterations": len(case["iterations"]),
            "artifacts": len(artifacts), "step_examples": len(case["iterations"]),
            "generated_candidates": sum(len(s["candidates"]) for s in case["iterations"]),
            "search_entries": len(records)}


def search(library, query, limit=10, include_synthetic=False):
    tokens = list(dict.fromkeys(re.findall(r"[^\W_]{3,}", query, re.UNICODE)))[:40]
    if not tokens:
        return []
    expression = " OR ".join('"' + t.replace('"', '""') + '"' for t in tokens)
    # Read-only SQLite URI: lookup cannot create a library or call the network.
    uri = (Path(library) / "index.sqlite").resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        rows = db.execute("SELECT record, bm25(examples) FROM examples WHERE examples MATCH ? ORDER BY bm25(examples)",
                          (expression,))
        result = []
        for serialized, relevance in rows:
            record = json.loads(serialized)
            if record["kind"] == "synthetic_example" and not include_synthetic:
                continue
            result.append({"retrieval_score": -relevance, **record})
            if len(result) >= limit:
                break
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("bake")
    s.add_argument("--case", required=True); s.add_argument("--library", required=True)
    s.add_argument("--deny-file", help="Private JSON array of original product/customer identifiers")
    s = sub.add_parser("search")
    s.add_argument("--library", required=True); s.add_argument("--query", required=True)
    s.add_argument("--limit", type=int, default=10); s.add_argument("--include-synthetic", action="store_true")
    args = p.parse_args()
    if args.command == "bake":
        denied = read(args.deny_file) if args.deny_file else []
        if not isinstance(denied, list) or any(not isinstance(t, str) or not t.strip() for t in denied):
            raise ValueError("deny-file must be a JSON array of nonempty strings")
        result = bake(args.case, args.library, denied)
    else:
        if not 1 <= args.limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        result = search(args.library, args.query, args.limit, args.include_synthetic)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
