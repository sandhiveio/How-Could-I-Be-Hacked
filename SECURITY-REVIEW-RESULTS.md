# Security review results

| Project or benchmark | Results | Issue types |
| --- | ---: | --- |
| ZizkaDB | 5 findings | API key authorization, session isolation, retention policy enforcement, import integrity |
| mattpocock/skills | 1 finding | Command policy bypass |
| google-research/paper-orchestra | 2 findings | Upload path containment, HTML escaping |
| elementalsouls/Claude-BugHunter | 1 finding | State-changing requests in default API inspection |
| cloudflare/security-audit-skill | 1 finding | JSON validator memory exhaustion |
| nvm-sh/nvm | 1 finding | Credential forwarding across origins in an alternate downloader |
| obra/superpowers | 1 finding | Unhandled WebSocket event serialization failure |
| addyosmani/agent-skills | 2 findings | Evaluation result path containment, fixture cleanup through symlinks |
| google-labs-code/stitch-skills | 1 finding | SSRF through incomplete destination address validation |
| Donchitos/Claude-Code-Game-Studios | 2 findings | Advisory write policy bypass through path normalization gaps, audit-log record injection |
| Read-only filesystem browser | 2 findings | Mount containment across operations and link handling during recursive reads |
| PatchEval-Verified | 27 cases | Injection, authentication and authorization flaws, credential exposure, SSRF, request smuggling, path traversal, denial of service, signature validation flaws |
| AgentDojo | 4 cases | Indirect prompt injection |
| Terminal-Bench | 3 cases | Information exposure, anonymization consistency, HTML sanitization |

Project findings were confirmed in local checks. Benchmark counts reflect cases investigated.

Recent review examples and their regression assertions are linked from the
[full case catalog](CASE-CATALOG.md#defensive-review-examples). Source checks used pinned snapshots and
local fixtures. Their results describe the reviewed revisions. The downloader review retained
a file-permission assertion failure reproduced on both baseline and repaired copies.

Two additional anonymized cases cover equivalent payment destinations and how helper processes
receive imported data. The payment review includes regression results on a local working copy.
The helper-process review records results from an isolated harness.

[Back to How Could I Be Hacked](README.md)
