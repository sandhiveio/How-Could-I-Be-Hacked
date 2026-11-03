#!/usr/bin/env python3
"""Offline trajectory inspection and private assessment scaffolding; never executes tests."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from offline_io import read

DEFAULT_LIBRARY = Path(__file__).resolve().parents[1] / "library"


def contained(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Path must remain inside the selected library")
    return path


def inventory(root):
    cases = sorted((root / "cases").glob("case-*"))
    steps = sorted((root / "cases").glob("*/iterations/*/step.json"))
    with closing(sqlite3.connect((root / "index.sqlite").resolve().as_uri() + "?mode=ro", uri=True)) as db:
        entries = db.execute("SELECT count(*) FROM examples").fetchone()[0]
    return {"cases": len(cases), "steps": len(steps), "search_entries": entries,
            "checklists": len(list((root / "checks").glob("*.md"))),
            "retrieval": "offline SQLite FTS5 lexical search"}


def verify(root):
    failures = []
    manifests = sorted((root / "cases").glob("*/manifest.json"))
    if not manifests:
        failures.append("No case manifests found")
    checked = 0
    for manifest in manifests:
        for entry in read(manifest)["artifacts"]:
            path = contained(manifest.parent, entry["path"])
            checked += 1
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                failures.append(str(path.relative_to(root)))
    with closing(sqlite3.connect((root / "index.sqlite").resolve().as_uri() + "?mode=ro", uri=True)) as db:
        integrity = [r[0] for r in db.execute("PRAGMA integrity_check")]
    if integrity != ["ok"]:
        failures.extend(integrity)
    return {"ok": not failures, "checked_artifacts": checked, "failures": failures}


def validate_assessment(path):
    doc = read(path)
    errors = []
    for key in ("target", "scope"):
        if not isinstance(doc.get(key), str) or not doc[key].strip():
            errors.append(f"{key}: nonempty string required")
    items = doc.get("hypotheses")
    if not isinstance(items, list) or not items:
        errors.append("hypotheses: at least one record required")
        items = []
    ids = set()
    for i, item in enumerate(items):
        prefix = f"hypotheses[{i}]"
        if not isinstance(item, dict):
            errors.append(prefix + ": object required")
            continue
        for key in ("id", "hypothesis", "applicability", "test", "expected", "falsifier", "control"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"{prefix}.{key}: nonempty string required")
        sid = item.get("id")
        if isinstance(sid, str):
            if sid in ids:
                errors.append(prefix + ": duplicate id")
            ids.add(sid)
        for key in ("source_references", "code_locations"):
            value = item.get(key)
            if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x.strip() for x in value):
                errors.append(f"{prefix}.{key}: nonempty string array required")
        status = item.get("status")
        if status not in ("supported", "refuted", "inconclusive", "not_executed"):
            errors.append(prefix + ": invalid status")
        evidence = item.get("evidence")
        if not isinstance(evidence, list):
            errors.append(prefix + ": evidence array required")
            evidence = []
        if status in ("supported", "refuted", "inconclusive") and not evidence:
            errors.append(prefix + ": executed status requires actual evidence")
        if status == "not_executed" and evidence:
            errors.append(prefix + ": unexecuted hypothesis cannot carry execution evidence")
        for entry in evidence:
            if not isinstance(entry, dict):
                errors.append(prefix + ": evidence object required")
                continue
            for key in ("command", "output_artifact", "interpretation"):
                if not isinstance(entry.get(key), str) or not entry[key].strip():
                    errors.append(f"{prefix}.evidence.{key}: nonempty string required")
            output = entry.get("output_artifact")
            if isinstance(output, str) and not (path.parent / output).is_file():
                errors.append(prefix + ": output artifact does not exist")
    return {"ok": not errors, "errors": errors}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--library", type=Path, default=DEFAULT_LIBRARY)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("stats")
    sub.add_parser("verify")
    s = sub.add_parser("show")
    s.add_argument("--step", required=True)
    s = sub.add_parser("trajectory")
    s.add_argument("--case", required=True)
    s = sub.add_parser("init-assessment")
    s.add_argument("--target", required=True)
    s.add_argument("--out", type=Path, required=True)
    s = sub.add_parser("validate-assessment")
    s.add_argument("--file", type=Path, required=True)
    args = p.parse_args()
    root = args.library.resolve()
    if args.command == "stats":
        result = inventory(root)
    elif args.command == "verify":
        result = verify(root)
    elif args.command == "show":
        result = read(contained(root, args.step))
    elif args.command == "trajectory":
        folder = contained(root / "cases", args.case)
        paths = sorted((folder / "iterations").glob("*/step.json"))
        if not paths:
            raise ValueError("No trajectory steps found")
        result = [read(contained(root, str(path))) for path in paths]
    elif args.command == "init-assessment":
        result = {"schema_version": 1, "target": args.target, "scope": "", "hypotheses": []}
        args.out.parent.mkdir(parents=True, exist_ok=True)
        with args.out.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    else:
        result = validate_assessment(args.file.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if isinstance(result, dict) and result.get("ok") is False else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, TypeError, sqlite3.Error) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        sys.exit(1)
