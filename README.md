<h1><img src="assets/illustrations/sandhive-emblem.jpg" width="40" height="40" alt="SandHive" /> How Could I Be Hacked</h1>

**Security checks from across GitHub for the PR you’re about to ship.**

Your coding agent adapts security checks from real open-source reviews to your PR diff.
It runs them locally and shows what they covered beyond your existing tests.

**121 investigation and review steps across 41 anonymized cases.** Local search and reports
run with Python and SQLite. **No separate API key required.**

[**Review a PR**](#quickstart) · [**See example report**](references/example-pr-report.md)

## What it adds to a PR

In ItsDangerous PR #442, a library step expanded **two text-token checks into 12 combinations**
across serializer classes, unexpected keywords, and text and byte inputs. The reviewed code
rejected unexpected keywords in all 12 combinations. [Read the full report](references/example-pr-report.md)

## Quickstart

Install the PR-review version with the [Skills CLI](https://github.com/vercel-labs/skills#install-a-skill).

```sh
npx skills add 'sandhiveio/How-Could-I-Be-Hacked#codex/pr-review-library-evidence' --skill how-could-i-be-hacked
```

Open the branch you want to review in your coding agent and paste this prompt.

> Use $how-could-i-be-hacked to review the current branch against `main` before merge.
> Record the merge base and tested `HEAD`. Report what the library added beyond existing tests,
> the results, any fixes or regression tests needed before merge, and what still needs checking.

## How it works

1. **Read the diff.** Identify the security-sensitive behavior the PR changes and record the base and head commits.
2. **Find relevant cases.** Search the bundled library and select steps that apply to the changed behavior.
3. **Check locally.** Adapt those steps to the PR and record what ran and what happened.
4. **Report the results.** Show which checks the library added, what blocks merge, and what remains unchecked.

SandHive uses leading AI models to review recent code selected daily from public repositories
across GitHub. Checks and observations from those reviews become anonymized library steps.
Newly curated steps ship in updated snapshots. Update the skill to get the latest snapshot.

[Workflow diagram](assets/illustrations/investigation-workflow.svg) · [Investigation map](assets/illustrations/investigation-cover.svg)

## Case catalog

| Example | What the review checks |
| --- | --- |
| [Session revocation](library/cases/case-47e872f11dcc4421947ad049b5018bf8/case.json) | Whether existing tokens stop working after an account is disabled |
| [Secret redaction in logs](library/cases/case-8febf1af62cd40e6ba9dfea83f4728cd/case.json) | Whether application and SDK loggers mask credentials |
| [OIDC group membership](library/cases/case-1392ecdfbe2744d59acddd5bb54bc0d7/case.json) | Whether group membership is verified before forwarding configured groups |
| [Upload destination containment](library/cases/case-88fc403c29eb4697adbfc2d944b682fe/case.json) | Whether uploads and direct writes stay within the allowed directory |
| [Release artifact visibility](library/cases/case-5c4667fb970b4684ac569c5bb5a27533/case.json) | Whether shipped bundles, source maps, and provenance follow the source visibility policy |

[Full case catalog](CASE-CATALOG.md) · [Published security review results](SECURITY-REVIEW-RESULTS.md)

## Reference

### Review a module or repository

Give the skill a module path or the whole repository and name the security behavior you want
checked. The report records the revision, scope, findings, results, and gaps. [Review guide](references/review.md)

### Search the library directly

Run from the skill directory with Python 3.10+ and SQLite FTS5.

```sh
python scripts/corpus.py search --library library --query "credential masking formatter" --limit 5
```

### CLI and report format

Use `python scripts/toolkit.py stats` to check the installed snapshot or
`python scripts/toolkit.py verify` to check its integrity.
[Command reference](references/workflow.md) · [Report format](references/report-format.md) · [Library format](library/README.md)

For manual setup, copy the full repository into your agent’s skills directory under
`how-could-i-be-hacked`, or point your agent at [SKILL.md](SKILL.md).

[Offline iteration protocol](references/iteration.md) · [Library publication audit](references/workflow.md#publication-audit) · [MIT License for corpus materials](library/LICENSE)

## Contact

[SandHive on GitHub](https://github.com/sandhiveio) · [SandHive website](https://sandhive.io) · [@sandhive on Telegram](https://t.me/sandhive)
