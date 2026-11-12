#!/usr/bin/env python3
"""Index reviewed defensive cases and check publication coverage."""
import argparse
from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3

from corpus import scan, shape, text
from offline_io import read, write

DEFAULT_LIBRARY = Path(__file__).resolve().parents[1] / "library"
KIND = "defensive_case"
CONTEXT_KEYS = {"hint", "surface", "assumptions"}


def check_shape(doc, keys, where):
    shape(doc, keys, keys, where)


def load_case(path, case):
    case_id = path.parent.name
    check_shape(case, CONTEXT_KEYS | {"schema_version", "id", "kind", "title"}, str(path))
    if case["schema_version"] != 1 or case["id"] != case_id or not re.fullmatch(r"case-[0-9a-f]{32}", case_id):
        raise ValueError(f"Invalid defensive case identity at {path}")
    for key in ("title", "hint", "surface"):
        text(case[key], key)
    assumptions = case["assumptions"]
    if not isinstance(assumptions, list) or not assumptions:
        raise ValueError(f"Expected at least one assumption at {path}")
    for assumption in assumptions:
        text(assumption, "assumption")
    scan(case, ())

    context = {key: case[key] for key in sorted(CONTEXT_KEYS)}
    paths = sorted(path.parent.glob("iterations/*/step.json"))
    if len(paths) < 2:
        raise ValueError(f"Expected at least two defensive steps at {path}")
    records = []
    previous = None
    for number, step_path in enumerate(paths, 1):
        step = read(step_path)
        check_shape(step, {"schema_version", "kind", "title", "context", "review",
                           "source_observation", "lineage"}, str(step_path))
        ordinal = f"{number:04d}"
        iteration = f"iteration-{ordinal}"
        lineage = {"case_id": case_id, "iteration_id": iteration, "previous_iteration_id": previous}
        if (step["schema_version"] != 1 or step["kind"] != KIND or step["context"] != context
                or step["lineage"] != lineage or step_path.parent.name != ordinal):
            raise ValueError(f"Invalid defensive step context or lineage at {step_path}")
        text(step["title"], "step title")
        review = step["review"]
        check_shape(review, {"invariant", "verification"}, "review")
        observation = step["source_observation"]
        check_shape(observation, {"outcome", "summary"}, "source observation")
        if observation["outcome"] not in {"supported", "refuted", "inconclusive"}:
            raise ValueError(f"Invalid source observation outcome at {step_path}")
        for field in (review["invariant"], review["verification"], observation["summary"]):
            text(field, "defensive step text")
        scan(step, ())
        records.append({
            "kind": KIND, "case_id": case_id, "iteration_id": iteration,
            "title": step["title"], "case_title": case["title"], **context,
            "candidate": {"id": iteration, "text": review["invariant"]},
            "candidate_role": "defensive_review",
            "historical_evaluation": None, "historical_observation": None,
            "selected_in_source_case": False,
            "observation_scope": "Generalized source observation. Verify behavior in the code under review.",
            "artifact_directory": f"cases/{case_id}/iterations/{ordinal}",
            "review": review, "source_observation": observation,
        })
        previous = iteration

    manifest = {
        "schema_version": 1, "case_id": case_id, "iterations": len(paths),
        "artifacts": [{"path": artifact.relative_to(path.parent).as_posix(),
                       "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest()}
                      for artifact in [path, *paths]],
    }
    return manifest, records


def rows(library):
    manifests = {}
    entries = []
    for path in sorted((library / "cases").glob("*/case.json")):
        case = read(path)
        if case["kind"] != KIND:
            continue
        manifest, records = load_case(path, case)
        manifests[path.parent / "manifest.json"] = manifest
        for record in records:
            searchable = " ".join([record["case_title"], record["title"], record["hint"],
                                   record["surface"], *record["assumptions"],
                                   record["review"]["invariant"], record["review"]["verification"]])
            entries.append((searchable, json.dumps(record, ensure_ascii=False, sort_keys=True)))
    return manifests, entries


def indexed_defensive_rows(db):
    for row_id, searchable, payload in db.execute("SELECT rowid, search_text, record FROM examples"):
        record = json.loads(payload)
        if record["kind"] == KIND:
            yield row_id, searchable, json.dumps(record, ensure_ascii=False, sort_keys=True)


def index_errors(library, db):
    manifests, expected = rows(library)
    errors = [path.relative_to(library).as_posix() for path, manifest in manifests.items()
              if not path.is_file() or read(path) != manifest]
    actual = Counter((searchable, payload) for _, searchable, payload in indexed_defensive_rows(db))
    if actual != Counter(expected):
        errors.append("Defensive case rows differ from case files. Run defensive_cases.py index.")
    return errors


def refresh_index(library):
    manifests, entries = rows(library)
    uri = (library / "index.sqlite").resolve().as_uri() + "?mode=rw"
    with closing(sqlite3.connect(uri, uri=True)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        existing = list(indexed_defensive_rows(db))
        for path, manifest in manifests.items():
            if not path.is_file() or read(path) != manifest or b"\r\n" in path.read_bytes():
                write(path, manifest, newline="\n")
        if Counter((searchable, payload) for _, searchable, payload in existing) != Counter(entries):
            db.executemany("DELETE FROM examples WHERE rowid = ?",
                           [(row_id,) for row_id, _, _ in existing])
            db.executemany("INSERT INTO examples(search_text, record) VALUES (?, ?)", entries)
    return {"cases": len(manifests), "search_entries": len(entries)}


def case_counts(library):
    return {path.parent.name: len(list(path.parent.glob("iterations/*/step.json")))
            for path in (library / "cases").glob("*/case.json")
            if read(path)["kind"] != "synthetic_example"}


def audit(library, producer_library):
    public = case_counts(library)
    producer = case_counts(producer_library)
    if not producer:
        raise ValueError("Producer library has no case records")
    missing = sorted(producer.keys() - public.keys())
    different = sorted(case_id for case_id in producer.keys() & public.keys()
                       if producer[case_id] != public[case_id])
    expected_steps = {(case_id, read(path)["lineage"]["iteration_id"])
                      for case_id in public
                      for path in (library / "cases" / case_id).glob("iterations/*/step.json")}
    uri = (library / "index.sqlite").resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as db:
        errors = index_errors(library, db)
        indexed_steps = set()
        for payload, in db.execute("SELECT record FROM examples"):
            record = json.loads(payload)
            if record["kind"] != "synthetic_example":
                indexed_steps.add((record["case_id"], record["iteration_id"]))
    index_gaps = sorted({case_id for case_id, _ in expected_steps ^ indexed_steps})
    return {
        "ok": not (missing or different or index_gaps or errors),
        "producer_cases": len(producer), "public_cases": len(public),
        "missing_cases": missing, "different_step_counts": different,
        "index_gaps": index_gaps, "index_errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("index")
    check = commands.add_parser("audit")
    check.add_argument("--producer-library", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = (refresh_index(args.library) if args.command == "index"
                  else audit(args.library, args.producer_library))
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
        result = {"ok": False, "error": str(exc)}
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
