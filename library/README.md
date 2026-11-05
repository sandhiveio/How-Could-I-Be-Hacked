# SandHive local attack library

This directory is the offline, reusable output of a curated security-case trajectory. It
contains anonymous **step examples**: each step can be retrieved and understood without the
source case or the preceding steps.

The original corpus materials in this directory, including the curated examples,
are available under the [MIT License](LICENSE). Third-party materials remain
subject to their original license terms.

## Contents

- `index.sqlite` — local lexical full-text index over pre-action context and candidate actions.
- `cases/case-<id>/case.json` — anonymous case context, assumptions and plans.
- `cases/case-<id>/planning.json` — the initial plans and the selected plan.
- `cases/case-<id>/iterations/<nnnn>/step.json` — one independent capsule per executed step.
- `cases/case-<id>/manifest.json` — SHA-256 hashes of every exported case artifact.
- `checks/static-file-containment.md` — a reusable checklist derived from the executed case.

The exported case preserves three real iterations and all generated candidates, including a
poor candidate retained with its ineligible evaluation. Historical scores and observations
describe the **source case only**; they are hypotheses for a new target, not facts about it.

## Search locally

Run from the project root:

```bash
python scripts/corpus.py search --library library --query 'path traversal containment static root'
python scripts/corpus.py search --library library --query 'symlink inside root realpath'
python scripts/corpus.py search --library library --query 'extensionless index append branch'
python scripts/corpus.py search --library library --query 'query string concurrent requests'
```

The engine is lexical, not semantic. Try several formulations and synonyms. A retrieval hit
contains the pre-action hint, surface, assumptions, the candidate action, its historical
evaluation, and the observation only when that candidate was actually selected. Sibling
candidates have no observation because they were not executed.

## Use a retrieved step

1. Read the step's `context.hint` and `assumptions`; decide whether the trust boundary and
   permissions match the new target.
2. Compare the candidate actions, not their list positions or historical scores.
3. Adapt the promising mechanism to the new source and fixture. Do not copy product-specific
   names, routes, paths, versions or payload markers.
4. Execute one bounded local check and save the exact command, output, diff/artifact and
   interpretation, including failures.
5. Record the actual observation. Keep the step self-contained when exporting it again.

## Status and integrity

This library contains local, agent-supplied evidence only. It does **not** claim an official
benchmark pass: the external harness was not available inside the producing container. Treat
the observations as reproducible starting points that must be retested on the new target.

The case was curated from source material and baked with `scripts/corpus.py`. Source identity,
raw logs, private paths and the source-to-case mapping stay outside `library/`.
