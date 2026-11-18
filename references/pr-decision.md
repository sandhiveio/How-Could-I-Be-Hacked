# PR merge recommendation

Use this contract to turn a PR assessment into an actionable recommendation for its reviewed
revision and scope. Read the diff, identify changed security guarantees, and define the checks
needed to evaluate them. Search the library by these mechanisms, compare applicability, and
adapt relevant hypotheses, controls, or test designs into concrete additional assertions.

## Additional checks and lasting tests

Read the existing tests before claiming extra coverage. Explain the specific input, boundary,
state transition, or assertion that a selected library step adds. Running the existing suite
is useful regression evidence. An additional check must establish something the suite does
not already establish for this change, or expand that assertion to a relevant missing case.

Extend tests through the target's normal entry point when coverage is missing. For every
confirmed security defect introduced or exposed by the PR, add a persistent regression test
that fails on the reviewed revision and include a legitimate control. Record the fix required
and the test that must pass before merge. If a repaired revision is available, verify both
the reproducer and the control there in a new assessment of that revision.

Keep the test file or an applicable test patch and the exact command/output. Explain any
environment failure that prevents execution. Work in an isolated copy when source-snapshot
restrictions apply. Honor benchmark-specific editing permissions and official verdict rules.

An applicable library source can contribute a mechanism, a discriminating input, a control,
or the comparison design. Explain that contribution accurately. Set aside weak matches and
report missing library coverage when no retrieved step supports an additional relevant check.

## Check results

Keep the existing hypothesis `status` for supported/refuted/inconclusive/not_executed. Add
these fields to each check used for the PR recommendation.

```json
{
  "result": "pass",
  "result_reason": "Explain the actual observation against the desired security behavior.",
  "additional": true,
  "coverage_delta": "Name the extra assertion or case and the library step's contribution."
}
```

`result` is `pass`, `fail`, `inconclusive`, or `not_executed`. A test that rejects an expired
credential as intended has a passing safety result. A hypothesis that the expired credential
is accepted can be supported while its safety result is `fail`. Read the assertions and
output to make this judgment. A process exit code alone cannot determine the safety result.

Use `additional: false` for an existing-suite run. An executed additional check also needs
the normal evidence, source decisions, tested revision, and adaptation from [review.md](review.md).
Checks originating in local code analysis retain their own provenance.

## PR criteria, findings, and required tests

New PR assessments include `merge_review` with `rationale`, `library_value`, `criteria`,
`findings`, and `required_tests`. Fill `rationale` with the decision's technical basis and
scope. Explain the actual library contribution and its limits in `library_value`. Criteria
identify the behavior that needs to hold for the changed code. Mark optional criteria
explicitly and explain their scope in the description. Classify unfinished checks against
these criteria so their relevance to the recommendation stays visible.

```json
{
  "id": "criterion-1",
  "description": "Describe a changed security guarantee that must hold before merge.",
  "check_ids": ["check-1"],
  "required": true
}
```

Record a confirmed security finding with the following fields.

```json
{
  "id": "finding-1",
  "title": "Describe the concrete defect.",
  "severity": "high",
  "change_relation": "introduced",
  "impact": "Describe the affected actor, boundary, and consequence.",
  "recommendation": "Describe the repair needed before merge.",
  "check_ids": ["check-1"],
  "must_fix": true,
  "reason": "Explain why this issue blocks the reviewed change."
}
```

Severity is `critical`, `high`, `medium`, or `low`. `change_relation` is `introduced`,
`exposed_by_change`, `pre_existing`, or `unclear`. Establish attribution by comparing the base
and head or by tracing the changed path and recording the limits. Preserve original baseline
evidence separately from current-head evidence. Use `unclear` when attribution is unresolved.
Confirmed new findings and findings marked `must_fix` require current executed fail-result
evidence. An unrelated pre-existing finding can be recorded with `must_fix: false` and its
reason, while the review evaluates the current change's required guarantees.

Add required regression tests using these fields. The example is an incomplete planned test.

```json
{
  "id": "test-1",
  "description": "State the regression assertion and legitimate control.",
  "finding_ids": ["finding-1"],
  "check_ids": [],
  "status": "missing",
  "artifact": "",
  "sha256": "",
  "reason": "Explain what must be added before merge."
}
```

Test status is `missing`, `added`, or `passed`. An added or passed test references the saved
test file/patch in `artifact` and its SHA-256. Record the executed checks in `check_ids` after
the test runs. An added test can reproduce the current failure or await execution with its
reason recorded. A passed test needs current passing check results. `finding_ids` can be
empty for a required preventive test that fills a coverage gap. The report identifies a
missing regression requirement when a confirmed new or must-fix finding has no linked test.

## Recommendation

Run the normal validation and report commands. The report derives the recommendation from
the saved records and leads with the reasons, findings, required tests, and extra verified
behavior. Usage counts and detailed evidence follow.

For every selected source, the report traces its readable title and original hypothesis,
the applicability decision, the adapted current hypothesis, the extra assertion, test,
observed result, and evidence. It also shows the status and check reasons for each criterion.
Use these connections to explain why the result supports acceptance or a required fix.

Assess value concretely. A source may supply a missing mechanism, a control, or a comparison
method. Name that contribution and the coverage it added beyond the existing suite. A source
that only restates an existing check has a limited methodological contribution. The report
counts linked additional executions and library-informed new findings from the recorded
relationships. Those links explain provenance. A baseline comparison is needed to quantify
time saved or detection improvement. Keep findings from local analysis under their actual
origin, and describe unmeasured benefits as unmeasured.

| Recommendation | Basis |
| --- | --- |
| `request_changes` | A confirmed new/exposed security defect, another must-fix issue, a failed required check, a blocker, or a required test awaiting addition |
| `approve` | Scoped required criteria and required tests pass with current evidence, attribution is resolved, and a selected library source informed an additional executed passing check tied to the required criteria |
| `incomplete` | Missing scope/criteria, required tests awaiting execution, unevaluated or inconclusive required checks, unresolved attribution, or insufficient additional library-backed verification |

Describe acceptance as a recommendation for the reviewed scope and revision. List exactly
what was additionally checked, how, which source helped, and the observed result. Describe
coverage outside that scope in `gaps`. A confirmed blocker takes precedence over incomplete
verification, so the report can request its repair while showing the remaining checks.

Older schema 2 PR assessments remain readable. Add and evaluate this contract to obtain a
merge recommendation. Repository/module assessments report their checks without a PR merge
decision. Validation checks references, artifacts, results, and decision prerequisites. The
reviewer evaluates the actual assertion coverage, finding impact, and adequacy of evidence.
