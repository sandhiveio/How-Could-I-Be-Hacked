<h1><img src="assets/illustrations/sandhive-emblem.jpg" width="40" height="40" alt="SandHive" /> How Could I Be Hacked</h1>

Explore how your code could be attacked using real security investigation trajectories.
Find applicable hypotheses, run targeted checks, and turn verified findings into regression
tests — all locally, without API access.

**13 cases · 41 steps · 238 searchable hypothesis entries**

**Works offline. No API keys required.**

[Use with an agent](#use-with-an-agent) · [Run locally](#run-locally) · [Workflow](references/workflow.md)

![Branching investigation: competing hypotheses, discarded paths, a local experiment, evidence, and a regression test. Conceptual illustration.](assets/illustrations/investigation-cover.svg)

[View investigation map at full size](assets/illustrations/investigation-cover.svg)

## Spend fewer tokens. Reuse investigation paths.

Start from reusable investigation trajectories instead of rebuilding every hypothesis and test
plan from scratch. Retrieve a relevant mechanism, check its prerequisites against your code,
and adapt the existing test approach. This can save agent tokens and investigation time.

Use the library as a security review checklist: compare applicable attack paths, revisit
rejected alternatives, and add checks for overlooked trust boundaries and edge cases.
Build on previous investigations to cover more attack paths and reach useful results faster.
In our benchmarks, reusing investigation trajectories reduced token usage by 20% and sped up
case resolution.

## Use with an agent

![General investigation workflow: retrieve trajectories, check applicability, run a bounded experiment, record evidence, and iterate. Verified findings receive regression checks.](assets/illustrations/investigation-workflow.svg)

[View workflow at full size](assets/illustrations/investigation-workflow.svg)

Install the skill using the Skills CLI:

```sh
npx skills add sandhiveio/How-Could-I-Be-Hacked --skill how-could-i-be-hacked
```

Alternatively, copy or clone this repository into a folder named `how-could-i-be-hacked`
inside your agent's skills directory, or give your agent the absolute path to [SKILL.md](SKILL.md).
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

- Anonymous cases with independently readable investigation steps.
- Local lexical search, full trajectory inspection and artifact hash verification.
- Iterative planning, candidate evaluation, incumbent comparison and backtracking guidance.
- Private assessment scaffolding and evidence/step validation.

These counts describe the bundled snapshot; `stats` reports the current contents. Historical
outcomes are evidence about their source cases, not proof of a vulnerability in your code.
Search is lexical, not semantic, and cannot establish the absence of vulnerabilities.
The toolkit assists an agent; it does not autonomously scan code or execute retrieved text.

## Data and evidence

Snapshot: November 5, 2026. Daily library updates are planned; the update pipeline is not yet configured.

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
- Telegram: [@sandhive](https://t.me/sandhive)
