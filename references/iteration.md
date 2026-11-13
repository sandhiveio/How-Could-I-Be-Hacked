# Offline iterative protocol

This adapts planning, candidate evaluation, selection, observations and backtracking from
benchmark-creative-search/references/protocol.md. It is a consumer workflow, not a replacement
for the producer's mandatory API generation. The current agent performs reasoning and execution.

1. Save objective, scope, attacker permissions, current source facts and a finite budget (default
   five rounds). Form at least three materially different overall plans; compare prerequisites,
   discriminating tests and a path to the success criterion. Keep rejected plans with reasons.
2. At each round write a self-contained context and a direction question at overall, mechanism,
   experiment, implementation or verification level. Retrieve relevant library steps using English
   queries. Save the query and case/step/candidate references. Candidates can also come from local
   code analysis; label that origin explicitly rather than claiming library provenance.
3. Evaluate every new candidate and the incumbent with relevance, feasibility, information_gain,
   novelty and evidence in [0,1], eligibility and a reason. Reassess applicability to this target.
   Evidence scale: 0 untested, .25 inspected source, .5 local causal test, .75 discriminating
   regression, 1 demonstrated official criterion with actual harness output. File existence alone
   does not justify a score. Never transfer an executed sibling's evidence to another candidate.
4. Compare eligible candidates with common weights. At progress p = round / budget, use
   relevance .25, feasibility .20, information_gain .25-.15p, novelty .15-.10p,
   evidence .15+.25p. Historical retrieval scores do not enter this calculation. Retain an
   incumbent if alternatives add no useful information; ties need an explicit mechanism-based
   rationale, never list position. These are judgment aids, not calibrated probabilities.
5. Select one bounded next action. Before running it define inputs, setup, supporting result,
   falsifier, control and cleanup. Execute using the target's normal local tools. Save command,
   output or structured result, relevant diff and interpretation. Record only the selected
   action's observation. Use a fresh result artifact for each check and record its exit code.
6. Update context using the observation, then retrieve and evaluate again. Complete at least two
   real iterations for a trajectory; after early success use the second for a discriminating
   regression or robustness check. A shorter interrupted review remains partial. Stop at the
   explicit budget or demonstrated criterion after required verification. Budget exhaustion
   means incomplete unless the success criterion was actually met.
7. On backtracking, preserve the failed step and set parent_step_id to an earlier step with a
   selected hypothesis; use a new branch_id and explain the failed premise in context. IDs must
   be unique, parents earlier, and no observations may be reassigned between branches.

Save each round as a complete JSON capsule (private assessment data, not corpus schema):

```json
{
  "step_id": "step-1",
  "parent_step_id": null,
  "branch_id": "main",
  "context": "Authorized disposable fixture; state the source facts and attacker permissions.",
  "direction": "Which local test distinguishes the remaining mechanisms?",
  "candidates": [{"id": "candidate-1", "origin": "local_analysis", "text": "Mechanism, prerequisites, bounded test, expected result and falsifier."}],
  "evaluations": [{"id": "candidate-1", "eligible": true, "relevance": 0.8, "feasibility": 0.8, "information_gain": 0.8, "novelty": 0.2, "evidence": 0.0, "evidence_files": [], "rationale": "Applicable but untested; selected for a discriminating test."}],
  "selected_id": "candidate-1",
  "observation": {"candidate_id": "candidate-1", "outcome": "inconclusive", "summary": "Describe only the action actually executed and its controls and limits.", "command": "exact local command", "evidence_files": ["output.txt"], "remaining_uncertainty": ["Next question"]}
}
```

The example is a format illustration, not evidence of execution. For an incumbent include it
in candidates with origin incumbent and rescore it. Run `scripts/validate_steps.py --file
<steps.json>` on an array of completed capsules. Evidence paths resolve relative to steps.json.
The validator checks structure, full evaluation coverage, selected eligibility, lineage and
nonempty evidence files. A command with no console output can use a nonempty result artifact
as evidence. For new records, add `observation.checks` with `command`, integer `exit_code`, and
`evidence_files` for each command. The observation command must match one check exactly. Each
check's evidence must also be listed on the observation. Existing records can omit `checks`.
Review the saved result before drawing a conclusion, including when the exit code is zero.
Report number of new mechanisms, executed checks and checks that changed the next decision;
do not count candidate replacement alone as useful progress.
