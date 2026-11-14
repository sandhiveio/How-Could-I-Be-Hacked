<h1><img src="assets/illustrations/sandhive-emblem.jpg" width="40" height="40" alt="SandHive" /> How Could I Be Hacked</h1>

**Give your coding agent real security investigations to draw on during code review.**

Search for cases that match the code you are reviewing. See which hypotheses were tried, what
the checks showed, and which alternatives were set aside. Use that context to design local checks
and turn confirmed findings into regression tests.

**37 anonymized cases · 113 investigation and review steps · 475 search entries**

The library and search tools run locally with Python and SQLite. No API key required.

[Quickstart](#quickstart) · [Security review results](#security-review-results) · [Case catalog](CASE-CATALOG.md) · [How it works](#how-it-works) · [Command reference](references/workflow.md)

## Quickstart

### Use with a coding agent

Install with the [Skills CLI](https://github.com/vercel-labs/skills#install-a-skill).

```sh
npx skills add sandhiveio/How-Could-I-Be-Hacked --skill how-could-i-be-hacked
```

Paste this prompt into your agent from the repository you are authorized to review.

> Use $how-could-i-be-hacked to review this repository. Find cases that match the code,
> explain which checks apply, and add regression tests for any findings you confirm locally.
> Save review notes and evidence privately.

For manual setup, copy the full repository into your agent's skills directory under
`how-could-i-be-hacked`, or point your agent at [SKILL.md](SKILL.md).

### Search the library directly

Run the search from a local copy of this repository.

```sh
python scripts/corpus.py search --library library --query "credential masking formatter" --limit 5
```

Search results include the context and historical evaluation for each match. The local tools
require **Python 3.10+ with SQLite FTS5** and use the Python standard library. On Windows you
can also run them in WSL.

## Security review results

| Project or benchmark | Results | Issue types |
| --- | ---: | --- |
| ZizkaDB | 3 findings | API key authorization, session isolation |
| mattpocock/skills | 1 finding | Command policy bypass |
| PatchEval-Verified | 27 cases | Injection, authentication and authorization flaws, credential exposure, SSRF, request smuggling, path traversal, denial of service, signature validation flaws |
| AgentDojo | 4 cases | Indirect prompt injection |
| Terminal-Bench | 3 cases | Information exposure, anonymization consistency, HTML sanitization |

Project findings were confirmed in local checks. Benchmark counts reflect cases investigated.

## How it works

1. **Search by mechanism.** The SQLite index looks for any of your query terms in case context
   and candidate hypotheses. Try synonyms when a query misses the terms used in the corpus.
2. **Read the evidence.** Investigation steps include candidate evaluations and the observation
   for the selected check. Defensive review steps include an invariant, a regression assertion,
   and a generalized source observation. Use the trajectory command to read the steps in order.
3. **Apply the relevant checks.** Compare the case's assumptions with your own code and collect
   fresh evidence before reporting a finding. Keep assessments private and work within the
   repository's authorized scope.

[![Security review workflow from library search to regression tests.](assets/illustrations/investigation-workflow.svg)](assets/illustrations/investigation-workflow.svg)

[View the branching investigation map](assets/illustrations/investigation-cover.svg).

## Library and tools

```sh
python scripts/toolkit.py stats
python scripts/toolkit.py verify
python scripts/test_toolkit.py
```

`stats` reports the contents of the installed snapshot. `verify` checks artifact hashes and SQLite
integrity. See the [library format](library/README.md), [command reference](references/workflow.md),
and [offline iteration protocol](references/iteration.md) for trajectory inspection and private
assessment validation.
Maintainers can check publication coverage with the [case audit](references/workflow.md#publication-audit).

The [public corpus and its original examples](library/LICENSE) are available under the MIT License.
The snapshot contains anonymized artifacts. Raw runs and private case mappings stay with the
producer.

## Contact

- [SandHive on GitHub](https://github.com/sandhiveio)
- [SandHive website](https://sandhive.io)
- [@sandhive on Telegram](https://t.me/sandhive)
