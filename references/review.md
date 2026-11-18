# Review scope and evidence reporting

Use this workflow for a repository, a module, or a specific PR. Keep the assessment and its
search/evidence artifacts in a private directory outside the installed skill. Commands below
run from the skill directory. The agent inspects code and runs the target's normal local tools.

## Establish the review scope

For repository/module mode, name the relevant paths, behaviors, permissions, and review
objective in `scope`. Record the actual tested revision from Git or an explicit source-tree
snapshot identity when the target has no Git history.

For PR mode, resolve the actual diff base and reviewed head to full commit IDs. Inspect the
diff and expand into the relevant callers, authorization, state changes, storage, migrations,
configuration, and tests as needed to evaluate the change. Describe how findings relate to
the diff, including existing problems encountered in the relevant code.

Record `review.tested_revision` from the working copy used for checks. A merge-result build
can have a different revision from the PR head. Record its build identity in `review.build_id`
when available. Updated PR commits require a new assessment of the affected checks. Preserve
the earlier assessment and its evidence under their original revision. Separate evidence for
different tested revisions into separate assessments.

```sh
python scripts/toolkit.py init-assessment --target /path/to/repo --out /private/review.json
python scripts/toolkit.py init-assessment --target /path/to/repo --mode pr --base <diff-base-sha> --head <reviewed-head-sha> --out /private/pr-review.json
```

Replace the angle-bracket values with resolved commit IDs. Initialization writes a schema 2
assessment and pins the installed library's SQLite SHA-256 and inventory. Fill `scope` before
validation. A PR assessment needs both revision arguments. Repository mode supports a scoped
review even when the target has no Git history.

## Save retrieval and decisions

```sh
python scripts/toolkit.py search-assessment --file /private/pr-review.json --query "account role session revocation" --limit 8
python scripts/toolkit.py search-assessment --file /private/pr-review.json --query "link destination containment" --mechanism "path containment" --limit 5
```

Each search saves a separate JSON receipt beside the assessment and adds its path, SHA-256,
query, mechanism filter, and limit to `searches`. Keep the installed snapshot available for
the duration of the assessment. Use another assessment after updating the library snapshot.
Search receipts retain the returned records, including historical outcomes and evaluations.

Each hit has a `source_id` formed from its case, iteration, and candidate IDs. Read the full
step context, applicability, test, and observation before recording a decision. Add a record
to `decisions` for each source actually assessed on the current code.

```json
{
  "source_id": "<source_id from the saved search>",
  "applicability": "Explain which current inputs, state, and code paths match the step.",
  "reason": "Explain why this source was selected or set aside.",
  "selected": true
}
```

Keep one decision per unique source ID across repeated searches. Selection means a source
informed the planned checks. Several sources can inform one check, and a source can inform
several checks. Preserve rejected decisions and their reasons. Historical observations describe
the source case. The new check requires its own result.

## Record the checks

Add records to `checks` using the fields below. The example illustrates the format. Replace
its values with the current assessment's actual setup and evidence.

```json
{
  "id": "check-1",
  "hypothesis": "State the assertion about current behavior being tested.",
  "origin": "library",
  "source_ids": ["<selected source_id>"],
  "code_locations": ["<path and line on the reviewed revision>"],
  "adaptation": "State the hypothesis and explain how the source step changed this check.",
  "test": "Describe the bounded setup, inputs, and procedure used on the current code.",
  "expected": "State the observation that would support this hypothesis.",
  "falsifier": "State the observation that would contradict it.",
  "control": "Describe the legitimate behavior used to detect unrelated breakage.",
  "status": "not_executed",
  "reason": "State the prerequisite needed before this planned check can run.",
  "revision": "<review.tested_revision>",
  "evidence": []
}
```

Checks from direct code analysis use `origin: "local_analysis"` and an empty `source_ids`
array. They remain useful when retrieval returns no applicable examples. A library check's
sources must have `selected: true` decisions. Record a source when it actually informs the
check, including a source that contributes a control or falsifier.

For an executed check, set `status` to `supported`, `refuted`, or `inconclusive` according to
the hypothesis and observation. Add evidence objects with `command`, integer `exit_code`,
`output_artifact`, `sha256`, and `interpretation`. Compute the hash from the saved output file.
Resolve artifact paths relative to the assessment. Preserve nonempty output or a structured
result file even when a command emits no console text. Keep pending checks `not_executed`
with empty evidence and explain the missing prerequisite in `gaps` or `blockers`.

Report untested behaviors as strings in `gaps`. Known release blockers use
`{"description": "...", "owner": "..."}` in `blockers`. Use `unassigned` if ownership is
unknown. Describe the impact under the stated permissions when a current check supports a
finding. Include the limits of the evidence and any unresolved compatibility questions.

## Generate the report

```sh
python scripts/toolkit.py validate-assessment --file /private/pr-review.json
python scripts/toolkit.py report-assessment --file /private/pr-review.json
python scripts/toolkit.py report-assessment --file /private/pr-review.json --format json
```

The report derives counts from the journal and links sources, applicability, adaptations,
commands, and current results. Count both unique search entries and unique steps. A normal
investigation step may have several indexed candidate hypotheses, so these totals can differ.

| Count | Meaning |
| --- | --- |
| Snapshot inventory | Cases, steps, and search entries in the pinned library |
| Retrieved | Unique returned sources across all saved searches |
| Considered | Sources with an applicability decision |
| Selected | Sources selected to inform planned checks |
| Used | Selected sources linked to at least one executed check with saved evidence |
| Executed | Checks with an actual result and evidence, including inconclusive checks |
| Pending | Planned checks with `not_executed` status |

A repeated source counts once in each source total. Count check records independently of
the number of sources and supporting commands. The report also groups current outcomes and
includes local-analysis checks, untested areas, and blocker owners. Retrieval and usage totals
describe the review process. State coverage through the behaviors examined and the explicit
gaps. Keep assertions about the tested revision tied to the working copy and actual outputs.

Validation checks structure, references, hashes, evidence files, and revision consistency.
The agent evaluates whether the recorded commands and observations support the conclusions.
Schema 1 assessments remain readable by `validate-assessment`. New journal/report commands
use schema 2. The anonymous library continues to use its own corpus format.
