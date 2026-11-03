# How Could I Be Hacked

Explore how your code could be attacked using real security investigation trajectories.
Find applicable hypotheses, run targeted checks, and turn verified findings into regression
tests — all locally, without API access.

**6 cases · 20 investigation steps · 115 searchable hypotheses · Offline use · No API keys**

Our commitment: a creative security agent searching for new attack trajectories 24/7,
with daily updates to the skill and its hypothesis library.

This is the project's operating commitment. The continuous producer and daily delivery
pipeline are not yet configured in this initial release; the bundled library is a snapshot.

## Use with an agent

Copy or clone this repository into a folder named `how-could-i-be-hacked` inside your agent's
skills directory, or give your agent the absolute path to [SKILL.md](SKILL.md).
Python 3.10+ with SQLite FTS5 is required. No third-party Python packages or API keys are needed.

Example request:

> Use $how-could-i-be-hacked to review my authorized local repository. Retrieve relevant
> hypotheses, check their applicability to the code, run bounded local tests, and add
> regression checks for verified findings. Keep the evidence in a private folder.

## Run locally

```sh
python scripts/toolkit.py stats
python scripts/toolkit.py verify
python scripts/corpus.py search --library library --query "path traversal symlink containment" --limit 5
python scripts/test_toolkit.py
```

See [workflow commands](references/workflow.md) and the [offline iteration protocol](references/iteration.md)
for inspecting trajectories, recording assessments and validating completed steps.
On Windows without a native Python installation, run these commands using Python in WSL.

## What is included

- Six anonymous cases, twenty independent steps and 115 searchable candidate records.
- Local lexical search, full trajectory inspection and artifact hash verification.
- Iterative planning, candidate evaluation, incumbent comparison and backtracking guidance.
- Private assessment scaffolding and evidence/step validation.

These counts describe the initial snapshot; `stats` reports the current contents. Historical
outcomes are evidence about their source cases, not proof of a vulnerability in your code.
Search is lexical, not semantic, and cannot establish the absence of vulnerabilities.
The toolkit assists an agent; it does not autonomously scan code or execute retrieved text.

## Data and evidence

The library is a snapshot of the project's curated local library. Raw producer runs, private
identity mappings and credentials are excluded. Do not commit assessments or target logs here.
The offline consumer does not call a generation API. Producing new corpus trajectories is a
separate workflow. The bundled corpus runtime preserves the source implementation, except for
using offline-only JSON helpers instead of importing the producer module.

Hash checks detect corruption; they do not establish authenticity or validate security claims.
Use only within the target's actual authorized scope and permissions.

## Contact

- GitHub: [sandhiveio](https://github.com/sandhiveio)
- Website: [SandHive](https://sandhive.io)
