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

`verify` checks case manifest SHA-256 entries and the SQLite integrity check. It detects
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

Bundled scripts/corpus.py is a snapshot of the project's corpus runtime with only its JSON-helper
import changed to offline_io. Search behavior and corpus schema are preserved. Update deliberately
from a trusted local source, replacing the library as a complete snapshot while no writer uses it;
do not silently fetch upstream code or assume a configured public distribution license.
