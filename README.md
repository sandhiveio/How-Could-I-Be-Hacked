<h1><img src="assets/illustrations/sandhive-emblem.jpg" width="40" height="40" alt="SandHive" /> How Could I Be Hacked</h1>

**Security checks from across GitHub for the PR you’re about to ship.**

Your coding agent adapts security checks from real open-source reviews to your PR diff and runs
them locally. The report shows what those checks covered beyond your test suite, what passed,
and what still needs checking.

**151 investigation and review steps across 56 anonymized cases.** Local search and reports
run with Python and SQLite. **No API key required.**

[**Review a PR**](#quickstart) · [**See example report**](skills/how-could-i-be-hacked/references/example-pr-report.md)

## Example PR review

ItsDangerous PR #442 added two tests for a change that rejects unexpected keyword arguments. A case from the library prompted the agent to compare the original code with the proposed fix across 12 combinations of serializer, keyword, and input type.

The original code accepted the unexpected arguments in all 12 combinations. The fix rejected them in all 12.

The library helped the reviewer verify that the fix held beyond the two examples in the PR, including when callers passed bytes instead of text.

[Read the full review](skills/how-could-i-be-hacked/references/example-pr-report.md)

## Quickstart

Install with the [Skills CLI](https://github.com/vercel-labs/skills#install-a-skill).

```sh
npx skills add sandhiveio/How-Could-I-Be-Hacked --skill how-could-i-be-hacked
```

Open the branch you want to review in your coding agent and paste this prompt.

> Use $how-could-i-be-hacked to review this branch against `main`. Show what you checked beyond
> the existing tests, what needs fixing before merge, and what’s still unverified.

## How it works

1. **Read the diff.** Identify the security-sensitive behavior the PR changes and record the base and head commits.
2. **Find relevant cases.** Search the bundled library and select steps that apply to the changed behavior.
3. **Check locally.** Adapt those steps to the PR and record what ran and what happened.
4. **Report the results.** Show which checks the library added, what blocks merge, and what remains unchecked.

SandHive reviews a daily selection of public GitHub code and turns useful checks into anonymized
cases. Update the skill to get the latest library snapshot.

[Workflow diagram](assets/illustrations/investigation-workflow.svg) · [Investigation map](assets/illustrations/investigation-cover.svg)

## Case catalog

| Example | What the review checks |
| --- | --- |
| [Session revocation](skills/how-could-i-be-hacked/library/cases/case-47e872f11dcc4421947ad049b5018bf8/case.json) | Whether existing tokens stop working after an account is disabled |
| [Secret redaction in logs](skills/how-could-i-be-hacked/library/cases/case-8febf1af62cd40e6ba9dfea83f4728cd/case.json) | Whether application and SDK loggers mask credentials |
| [OIDC group membership](skills/how-could-i-be-hacked/library/cases/case-1392ecdfbe2744d59acddd5bb54bc0d7/case.json) | Whether group membership is verified before forwarding configured groups |
| [Upload destination containment](skills/how-could-i-be-hacked/library/cases/case-88fc403c29eb4697adbfc2d944b682fe/case.json) | Whether uploads and direct writes stay within the allowed directory |
| [Release artifact visibility](skills/how-could-i-be-hacked/library/cases/case-5c4667fb970b4684ac569c5bb5a27533/case.json) | Whether shipped bundles, source maps, and provenance follow the source visibility policy |

[Full case catalog](CASE-CATALOG.md) · [Published security review results](SECURITY-REVIEW-RESULTS.md)

## Reference

### Review a module or repository

Give the skill a module path or the whole repository and name the security behavior you want
checked. The report records the revision, scope, findings, results, and gaps. [Review guide](skills/how-could-i-be-hacked/references/review.md)

### Search the library directly

Run from the repository root with Python 3.10+ and SQLite FTS5.

```sh
python skills/how-could-i-be-hacked/scripts/corpus.py search --library skills/how-could-i-be-hacked/library --query "credential masking formatter" --limit 5
```

### CLI and report format

Use `python scripts/toolkit.py stats` to check the installed snapshot or
`python scripts/toolkit.py verify` to check its integrity.
[Command reference](skills/how-could-i-be-hacked/references/workflow.md) · [Report format](skills/how-could-i-be-hacked/references/report-format.md) · [Library format](skills/how-could-i-be-hacked/library/README.md)

For manual setup, copy the full repository into your agent’s skills directory under
`how-could-i-be-hacked`, or point your agent at [SKILL.md](skills/how-could-i-be-hacked/SKILL.md).

[Offline iteration protocol](skills/how-could-i-be-hacked/references/iteration.md) · [Library publication audit](skills/how-could-i-be-hacked/references/workflow.md#publication-audit)

## Security and license

Report security or privacy issues through the channel described in the [security policy](SECURITY.md).

SandHive’s original skill, scripts, documentation, and library materials are available under the
[MIT License](LICENSE). Third-party materials remain subject to their original license terms.

## Contact

[SandHive on GitHub](https://github.com/sandhiveio) · [SandHive website](https://sandhive.io) · [@sandhive on Telegram](https://t.me/sandhive)
