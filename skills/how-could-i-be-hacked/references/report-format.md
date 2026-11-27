# Compact security review report

Use this format for the report a developer reads to decide what happens to the reviewed
change. The [review guide](review.md) defines evidence capture, and the
[merge contract](pr-decision.md) defines schema fields and recommendation prerequisites.
Keep the main report compact, with the full trace in an evidence appendix or JSON report.
See the [example PR report](example-pr-report.md) for a public excerpt from an actual run.

## Main report order

1. **Decision and pinned scope.** State `approve`, `request_changes`, or `incomplete` with one
   concise reason. Identify the repository/PR, actual diff base, reviewed head, and tested
   revision or build. State the code and behavior covered and the relevant execution environment.
2. **Library contribution.** Explain the actual coverage delta immediately below the decision.
   Name the mechanism, missing assertion, control, or comparison design supplied by the
   selected sources. Explain what was added beyond existing tests and what the results taught
   the reviewer. Then give compact retrieved/considered/selected/used counts and linked
   additional-check and finding counts. Keep unmeasured benefits explicitly unmeasured.
3. **Checked behavior.** Use one row per invariant, risk, or current-target hypothesis. Include
   code locations, library contribution or local-analysis origin, the bounded check, the
   observed result, and an evidence reference. A criterion can cite check IDs instead of
   repeating the same hypothesis. Show unexecuted and inconclusive checks with their next action.
4. **Findings and required actions.** Present confirmed security findings and functional
   observations with their kind and relation to this change visible. State the needed repair
   and mandatory regression test. Keep a pre-existing observation's attribution explicit.
5. **Tests, retest, and limits.** Link the saved preventive or defect-reproducing tests and
   record whether each is missing, added, or passed. Include an actual retest result when a
   fixed revision exists. End with unresolved scope, runtime, coverage, and environment limits.

The main report should let the reader follow this connection without opening the original chat.

```text
Changed guarantee and source location
  -> selected library step and reason it applies
  -> additional assertion or control
  -> executed check and observed result
  -> finding, preserved behavior, or unresolved question
  -> merge recommendation and next action
```

Use the existing `merge_review.rationale` for the decision's technical basis and
`merge_review.library_value` for the contribution and its limits. `coverage_delta` names the
extra assertion. The generated usage counts describe recorded retrieval and execution.
An existing-suite replay can provide regression evidence while contributing no new coverage
by itself. Identify checks originating in local analysis under their actual provenance.

## Checked-behavior table

Use concise rows that carry the facts needed to assess the result.

| Invariant, risk, and location | Contribution | Check and observed result | Evidence |
| --- | --- | --- | --- |
| State the changed guarantee and pinned file/line. | Cite the source step and the extra assertion, or identify local analysis. | Give the bounded method, current result, and material limitation. | Link the relevant command output or check record. |

The existing `checks` fields supply the hypothesis, code locations, test, control, result,
result reason, adaptation, and evidence. Criteria can use optional `risk` and
`code_locations` fields to make the reviewed consequence and source boundary explicit.
Keep each current hypothesis in one main-report row even when several sources informed it.
Preserve the separate supporting source links in the detail.

## Report skeleton

Use this skeleton with actual results. Omit empty finding and retest sections; retain any
unresolved required check or missing regression test. Keep the main text short and link detail.

```markdown
# PR security review — <repository / PR>

**<approve | request_changes | incomplete> — <scoped reason>**
Tested: <SHA / build>. Scope: <changed behavior and paths>. Environment: <runtime>.

## Library contribution
<Source step -> extra assertion beyond existing tests -> result -> effect on the decision.>
Retrieved / considered / selected / used: <unique entries and steps>.
Additional library checks: <executed / passed>; new security findings informed: <count>.
Snapshot: <identity and inventory; these counts do not measure security coverage>.

## Checked behavior
| Risk / hypothesis / location | Contribution | Check | Observed result / evidence |
| --- | --- | --- | --- |
| <guarantee, consequence, file:line> | <source step or local analysis> | <bounded method> | <pass/fail/inconclusive/not executed, observation, link> |

## Decision basis
<Why the required criteria support this decision; unresolved checks and next actions.>

## Security findings / functional observations
<ID, kind, severity or priority with reason, and relation to this change.>
<Location; preconditions; minimal reproduction and control; expected/observed behavior.>
<Impact; required repair; merge disposition; linked evidence; current remediation state.>

## Required tests and retest
<Test ID, assertion/control, missing/added/passed, artifact and execution evidence.>
<For an actual retest: fixed SHA, prior finding, observed result, assessment link.>

## Limits and evidence
<Untested behaviors, runtime/coverage limits; actual diff base and reviewed head.>
<Assessment, source decisions, commands, outputs and reusable tests.>
```

## Self-contained findings

A finding should be understandable and reproducible using its own description and linked
evidence. Record the following information together.

- The concrete failed guarantee, affected code location, and whether the PR introduced,
  exposed, or inherited the condition. Record uncertain attribution as uncertain.
- Preconditions and required access, a minimal local reproducer, and the legitimate control.
  Include expected behavior and what actually happened.
- The affected actor or resource, credible consequence, and the reason for the assigned
  security severity or functional priority.
- A specific correction and a persistent regression assertion, with its artifact and current
  execution state. Link the evidence checks that demonstrate the same finding.

Use `finding.kind`, `preconditions`, `reproduction`, `severity_reason`, and `code_locations`
when available. Older assessments can express the same information in `impact`, `reason`,
`recommendation`, and their referenced checks. These explanatory fields supplement the
existing schema and preserve its validation and evidence requirements.

A confirmed security finding requires current evidence for the failed safety behavior. A
functional observation remains identifiable as functional and uses a displayed priority.
Explain which finding blocks this change and why. A severity label alone supplies little
context for the merge decision, so include the concrete likelihood conditions and impact.

## Repairs and retests

Keep the preventive regression artifact even when an applicable check passes. For a confirmed
defect, preserve the failing reproducer and legitimate control on the reviewed revision. When
a fixing revision is supplied or produced within scope, assess that exact revision separately
and link its outputs to the original finding. Explain whether the original failure is closed,
still open, or remains unverified using those actual results. Preserve the original evidence
and cross-link the earlier and current assessments.

## Evidence detail and delivery

Move complete source hypotheses, applicability evaluations, historical observations, rejected
alternatives, test controls, commands, raw outputs, receipt lists, and full hashes into the
detail or JSON. Each main-report result should link to the specific supporting artifact.
Use stable check/finding IDs to avoid repeating lengthy descriptions across sections.
Give library-derived rows a compact source key that resolves to the exact selected source ID
and its saved applicability/adaptation record. A generic description such as "library-guided"
is insufficient to identify which step contributed.

Keep the Markdown file beside the assessment and use artifact paths relative to that
directory. Bundle those dependencies for an external reader. Use repository-relative file/line
references or source URLs pinned to the reviewed commit. Provide execution commands and
fixture/setup details sufficient to rerun the checks in an equivalent environment.
The optional `review.reproduction_guide` artifact can provide this recipe. Distinguish replay
of saved outputs from a fresh execution against the target, and use a fresh output directory
when scripts deliberately refuse to overwrite evidence.

Review delivery copies for private paths, identifiers, and secrets. Preserve raw hashed
evidence unchanged and redact a separate delivery copy with its own manifest when needed.
Describe inaccessible evidence, unavailable runtimes, untested paths, and scope restrictions
as explicit limits of the conclusion. The JSON report can retain private workspace paths
and should receive the same delivery review before external sharing.

## Examples from completed reviews

### Compatibility evidence from a base/head comparison

A serializer review compared the documented argument contract on the base and reviewed
revisions. The upstream suite passed all 299 tests on the reviewed revision. A separate
matrix expanded two upstream assertions to 12 input combinations and confirmed the intended
behavior change in all 12. Another 104 control observations matched across revisions.

Report this as one additional executed check with 12 comparison cases. Credit the upstream
suite separately. An alternate-salt file-loading failure appeared on both revisions and was
recorded as a pre-existing functional observation. The evidence supported scoped acceptance
and established no new security finding.

### Delivery validation from saved evidence

A delivery check resolved all 20 relative artifact links, replayed the report from saved
outputs successfully, and verified that the original evidence was unchanged. Record these
results under report delivery. The target verification remains tied to the original tested
revision. A fresh target run or repair retest requires its own execution evidence.
