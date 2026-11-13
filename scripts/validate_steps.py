#!/usr/bin/env python3
"""Validate completed offline iteration capsules; never runs tests or contacts services."""
import argparse
import math
from pathlib import Path
import sys
from offline_io import read

METRICS = ("relevance", "feasibility", "information_gain", "novelty", "evidence")


def validate(records, base):
    errors, seen = [], set()
    def require(condition, message):
        if not condition:
            errors.append(message)
    def nonempty(value):
        return isinstance(value, str) and bool(value.strip())
    def evidence(files, label):
        require(isinstance(files, list), label + ": evidence_files array required")
        paths = set()
        if isinstance(files, list):
            for entry in files:
                if not nonempty(entry) or not (base / entry).is_file():
                    errors.append(label + ": evidence file missing")
                    continue
                path = (base / entry).resolve()
                require(path.stat().st_size > 0, label + ": evidence file empty")
                paths.add(path)
        return paths
    if not isinstance(records, list) or len(records) < 2:
        return ["A completed trajectory requires an array of at least two actual steps"]
    for i, step in enumerate(records):
        label = f"step[{i}]"
        if not isinstance(step, dict):
            errors.append(label + ": object required")
            continue
        sid = step.get("step_id")
        require(nonempty(sid) and sid not in seen, label + ": unique step_id required")
        parent = step.get("parent_step_id")
        require(parent is None or isinstance(parent, str) and parent in seen, label + ": parent must name an earlier step")
        for key in ("branch_id", "context", "direction"):
            require(nonempty(step.get(key)), label + ": " + key + " required")
        candidates = step.get("candidates", [])
        evaluations = step.get("evaluations", [])
        if not isinstance(candidates, list) or not isinstance(evaluations, list):
            errors.append(label + ": candidates and evaluations must be arrays")
            continue
        ids = []
        for c in candidates:
            if not isinstance(c, dict):
                errors.append(label + ": candidate object required")
                continue
            for key in ("id", "origin", "text"):
                require(nonempty(c.get(key)), label + ": candidate " + key + " required")
            if isinstance(c.get("id"), str):
                ids.append(c["id"])
        require(bool(ids) and len(set(ids)) == len(ids), label + ": nonempty unique candidates required")
        evaluated = []
        eligible = set()
        for e in evaluations:
            if not isinstance(e, dict):
                errors.append(label + ": evaluation object required")
                continue
            eid = e.get("id")
            require(isinstance(eid, str), label + ": evaluation id required")
            if isinstance(eid, str):
                evaluated.append(eid)
                if e.get("eligible") is True:
                    eligible.add(eid)
            require(isinstance(e.get("eligible"), bool), label + ": eligibility boolean required")
            require(nonempty(e.get("rationale")), label + ": rationale required")
            for key in METRICS:
                value = e.get(key)
                require(type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1, label + ": invalid " + key)
            files = e.get("evidence_files")
            evidence(files, label)
            if type(e.get("evidence")) in (int, float) and e["evidence"] > 0:
                require(bool(files), label + ": positive evidence score requires saved evidence")
        require(sorted(evaluated) == sorted(ids), label + ": evaluate every candidate exactly once")
        selected = step.get("selected_id")
        require(isinstance(selected, str) and selected in eligible, label + ": selection must be eligible")
        obs = step.get("observation")
        if not isinstance(obs, dict):
            errors.append(label + ": observation object required")
        else:
            require(obs.get("candidate_id") == selected, label + ": observation belongs to selection only")
            require(obs.get("outcome") in ("supported", "refuted", "inconclusive"), label + ": actual outcome required")
            for key in ("summary", "command"):
                require(nonempty(obs.get(key)), label + ": observation " + key + " required")
            observation_paths = evidence(obs.get("evidence_files"), label)
            require(bool(obs.get("evidence_files")), label + ": completed action requires evidence")
            if "checks" in obs:
                checks = obs["checks"]
                if not isinstance(checks, list) or not checks:
                    errors.append(label + ": checks must be a nonempty array")
                else:
                    commands = set()
                    for check in checks:
                        if not isinstance(check, dict):
                            errors.append(label + ": check object required")
                            continue
                        command = check.get("command")
                        if nonempty(command):
                            commands.add(command)
                        else:
                            errors.append(label + ": check command required")
                        require(type(check.get("exit_code")) is int, label + ": check exit_code must be an integer")
                        check_paths = evidence(check.get("evidence_files"), label + ": check")
                        require(bool(check_paths) and check_paths <= observation_paths,
                                label + ": check files must belong to the observation")
                    command = obs.get("command")
                    require(nonempty(command) and command in commands,
                            label + ": observation command must match a recorded check")
            remaining = obs.get("remaining_uncertainty")
            require(isinstance(remaining, list) and all(nonempty(x) for x in remaining), label + ": remaining_uncertainty string array required")
        if nonempty(sid):
            seen.add(sid)
    return errors


if __name__ == "__main__":
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True)
    args = parser.parse_args()
    try:
        errors = validate(read(args.file), args.file.resolve().parent)
        print(json.dumps({"ok": not errors, "errors": errors}, indent=2))
        sys.exit(bool(errors))
    except (ValueError, OSError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        sys.exit(1)
