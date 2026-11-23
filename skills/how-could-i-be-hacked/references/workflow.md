# Commands and assessment workflow

Run these commands from the root of the skill. Replace the example target and output paths with
your own. `toolkit.py` uses the bundled library by default. Pass `--library PATH` before the
subcommand to select another library.

```powershell
python scripts/toolkit.py stats
python scripts/toolkit.py verify
python scripts/toolkit.py trajectory --case case-ID
python scripts/toolkit.py show --step cases/case-ID/iterations/0001/step.json
python scripts/toolkit.py init-assessment --target ../target-repo --out ../private/review.json
python scripts/toolkit.py init-assessment --target ../target-repo --mode pr --base DIFF_BASE_SHA --head HEAD_SHA --out ../private/pr-review.json
python scripts/toolkit.py search-assessment --file ../private/review.json --query "session revocation authorization" --limit 8
python scripts/toolkit.py validate-assessment --file ../private/review.json
python scripts/toolkit.py report-assessment --file ../private/review.json
```

`verify` checks case manifest SHA-256 entries, SQLite integrity, and whether the indexed defensive
entries match the case files. It detects
accidental corruption, not authenticity, anonymity or scientific validity. It does not repair
or rebuild the index. `trajectory` preserves chronological order; branch parents are in lineage.
`show` and `trajectory` accept only paths contained in the selected library.

Initialization creates a schema 2 assessment with a library snapshot, review scope, retrieval
receipts, source decisions, and checks. Fill scope and review records before validation. PR
mode needs resolved diff-base and head commit IDs. Read the [review guide](review.md) for the
exact fields, evidence hashes, source/check relationships, count definitions, and revision
rules. `report-assessment --format json` provides a structured report. A review with no
applicable sources can record checks originating in local analysis and the remaining gaps.
PR initialization also scaffolds `merge_review`. Fill its scoped criteria, finding attribution,
and required regression tests using the [merge recommendation contract](pr-decision.md).
The report derives an acceptance, change-request, or incomplete recommendation from these
records. Older PR assessments can add this section after evaluating their evidence and scope.

Legacy schema 1 assessments use hypothesis records with source references, applicability,
test, expected result, falsifier, control, status, and evidence. `validate-assessment` continues
to check them. The report and saved-search workflow use schema 2.

Validation checks the recorded structure and artifacts. The agent assesses relevance,
accuracy, language, and whether outputs support the conclusions. Keep the private assessment
separate from the anonymous corpus export described below.

The package is portable: copy this entire folder and point an agent at SKILL.md. To make it
skill-discoverable, place the folder in that agent's configured skills directory. No global
installation or remote update is performed by this package. Keep private assessment outputs
outside this folder. The snapshot contains only library artifacts, no raw producer runs.

Bundled `scripts/corpus.py` uses local SQLite and the `offline_io` JSON helpers.
Use `corpus.py search --library library --mechanism "path containment" --limit 5` to retrieve
reviewed steps by a specific mechanism. Add `--query` to rank matching tagged steps by text.
Steps without tags remain accessible through text search. Equal text scores use a stable order.

## Publication audit

For each source case in a publication, retain its existing anonymous ID and step count in the
public library. Author reviewed defensive case files using the same format as existing
`defensive_case` directories. Each step includes the case context, an invariant, a regression
assertion, and a generalized observation with its recorded outcome. Keep exploit procedures,
payloads, raw output, and source identity in the producer workspace. Review the full public
text before indexing it. Add optional `mechanism_tags` to the defensive step JSON using short,
lowercase English labels for mechanisms established by that step. Reuse existing labels for
the same mechanism.

```sh
python scripts/defensive_cases.py index
python scripts/toolkit.py verify
python scripts/defensive_cases.py audit --producer-library /path/to/opencode-near/workspace/library
```

The index command refreshes defensive manifests and SQLite entries from the reviewed files.
The audit exits nonzero on missing source case IDs, differing step counts, missing index entries,
or stale defensive rows. Run it on the host with both libraries available before publishing.
Commit the case artifacts and the updated SQLite index together.
