# SandHive local attack library

This directory contains curated security investigations for offline use. Each anonymous
investigation step can be retrieved and understood independently of the source case and the
preceding steps.

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
- [Defensive review examples](checks/defensive-review-examples.md) for identity, authorization,
  file handling, process arguments, database queries, outbound requests, configuration, and
  releases. Open these checklists directly. The SQLite index covers the case artifacts.

Each trajectory preserves multiple investigation steps and records why candidates were
selected, rejected, or ruled ineligible. Historical scores and observations describe the
source case. Use them to form hypotheses for a new target.

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

Check each case's observations for the evidence collected and the remaining uncertainty.
Retest applicable observations on the new target.

The indexed cases were curated from source material and baked with `scripts/corpus.py`. Source
identities, raw logs, private paths and source-to-case mappings stay outside `library/`.
