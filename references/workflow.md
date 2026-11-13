# Commands and assessment workflow

Commands work from any directory when invoked with absolute script paths. `toolkit.py` defaults
to the sibling library; `--library PATH` before the subcommand selects another library.

```powershell
python C:/workdir/sec/how-could-i-be-hacked/scripts/toolkit.py stats
python C:/workdir/sec/how-could-i-be-hacked/scripts/toolkit.py verify
python C:/workdir/sec/how-could-i-be-hacked/scripts/toolkit.py trajectory --case case-ID
python C:/workdir/sec/how-could-i-be-hacked/scripts/toolkit.py show --step cases/case-ID/iterations/0001/step.json
python C:/workdir/sec/how-could-i-be-hacked/scripts/toolkit.py init-assessment --target C:/path/to/authorized/repo --out C:/private/review.json
python C:/workdir/sec/how-could-i-be-hacked/scripts/toolkit.py validate-assessment --file C:/private/review.json
```

`verify` checks case manifest SHA-256 entries, SQLite integrity, and whether the indexed defensive
entries match the case files. It detects
accidental corruption, not authenticity, anonymity or scientific validity. It does not repair
or rebuild the index. `trajectory` preserves chronological order; branch parents are in lineage.
`show` and `trajectory` accept only paths contained in the selected library.

An initialized assessment is deliberately incomplete. Fill scope and hypothesis records before
validation. Each record needs an id, English hypothesis, source references (case/step/candidate),
code locations, applicability, bounded test, expected result, falsifier, control, status and
actual evidence. Evidence for executed checks contains command, output artifact and interpretation.
Evidence paths are private local references; the validator checks existence, not evidential truth.
Validation is structural; the agent must assess relevance, accuracy, language and completeness.
An assessment is not the corpus export schema and cannot be passed directly to corpus.py bake.

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
