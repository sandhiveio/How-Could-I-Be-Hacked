# Defensive review examples

These examples distill implementation checks from the OpenCode library. Each describes the
invariant to review and the expected behavior to verify in the repaired code.

## Account-level sign-in limits

**Applies when** an identity provider accepts multiple sign-in identifiers for one account
and the application enforces account-level limits on failed sign-ins.

**Review the identity boundary.** Follow account resolution through the lockout check and
the attempt-store update. Both operations should use the same stable account ID from the
provider. Check that identifiers the provider treats as distinct remain distinct. Review
whether concurrent failures update the shared account counter atomically. Preserve the
existing response contract for unknown accounts and invalid credentials.

**Regression assertions.** Verify that the provider maps all supported identifiers for one
fixture account to the same ID. At the rate limiter boundary, verify that updates for that
ID share one budget, concurrent increments are retained, and a second account has its own
budget. Use a controlled clock to verify that the lockout expires according to policy. Check
that valid sign-ins still succeed for an unlocked account.

## Archive extraction containment

**Applies when** an extractor accepts archives from outside its trust boundary and writes
entries beneath a caller-selected directory.

**Review the filesystem boundary.** Inspect every filesystem operation the extractor can
perform, including link handling and metadata updates. Each operation should be confined
to the destination at the point it runs. Prefer root-relative filesystem operations that
enforce containment while resolving path components. Permit only the entry types required
by the format and the application, and check that error handling preserves pre-existing files.

**Regression assertions.** Extract a benign archive with nested directories and regular files
into a temporary destination. Compare the expected tree and file contents and verify that a
separate sibling fixture stays byte-for-byte identical. If the product supports symbolic
links, verify the documented behavior for a link whose target is inside the destination.
At the filesystem abstraction, verify that a denied operation causes extraction to fail
and that any cleanup follows the documented ownership rules.

## Transcoder process arguments

**Applies when** a wrapper passes caller-provided media paths, filter settings, or numeric
options to an external transcoder.

**Review the process boundary.** Trace each public operation to process creation. Use a
trusted executable with an argument-vector API and shell execution disabled. Keep wrapper
options separate from values and validate each value according to the transcoder's option
or filter grammar. Check that input and output paths are handled according to the wrapper's
filesystem policy.

**Regression assertions.** Use a recording process stub and compare the full argument array
for legitimate inputs, including a filename with spaces, Unicode overlay text, and numeric
settings. Verify the executable and shell configuration for each public operation. Confirm
that invalid typed settings are rejected before process creation and that the wrapper reports
a nonzero exit status through its existing error contract.

## OIDC client-secret redaction

**Applies when** a service exposes a sanitized configuration through logs or a management
endpoint, and stores OIDC provider settings in a keyed collection.

**Review the redaction boundary.** Inspect how the sanitized copy is built and which outputs
use it. Mask each nonempty client secret in the copy, including providers added during reload.
Preserve empty values and public provider settings. Verify that redaction leaves the active
configuration intact for authentication.

**Regression assertions.** Use a fixture with two providers containing fake secrets and a
third with an empty secret. Assert that startup logs, reload logs, and the management response
contain the expected redacted fields. Check that issuer URLs, scopes, and provider identifiers
remain visible and that the authentication client still reads its configured secret.

## OIDC group membership

**Applies when** an identity adapter combines configured group names with user-info claims
and separately derives membership from project data.

**Review membership provenance.** If configuration defines which identity-provider groups
may be forwarded, require the user's verified claim to attest each forwarded group.
Check the handling of missing or malformed claims. Trace the final session groups to both
authorization decisions and forwarded identity headers, and preserve the separate rules for
project-derived membership.

**Regression assertions.** Stub the identity provider and the project service. Verify that
an attested configured group appears in the session and forwarded headers, that an omitted
group is absent, and that a valid project membership is preserved. Exercise a missing claim
and verify that it grants no claim-derived groups.

## List query fields and sorting

**Applies when** list endpoints accept filter fields or sort keys that become SQL identifiers
or ordering expressions.

**Review the query boundary.** Resolve external field names through server-owned mappings
to supported columns. Constrain filter operators and sort directions to supported choices
and keep filter values bound as parameters. Apply the same rules to all list handlers using
the query builder.

**Regression assertions.** Check generated queries for a supported filter and for both
supported sort directions. Assert that values are passed separately as bound parameters.
Use an unknown field name and a stub repository to verify that validation rejects the
request before issuing a query.

## Release artifact visibility

**Applies when** a release pipeline ships bundles, source maps, and a provenance manifest
under a source visibility policy.

**Review the release boundary.** Use the policy and the final output inventory to decide
which source metadata can ship. Check the actual published files, including embedded map
data and manifest references. Keep runtime secrets out of bundled literals and normalize
published provenance paths to a repository-relative form.

**Regression assertions.** Build a fixture with public and private modules and synthetic
markers for private source content. Check that the client map resolves to approved public
sources, and inspect all shipped artifacts for private source names, synthetic markers, and
absolute build paths. Smoke-test the built client and server entry points.

## Upload destination containment

**Applies when** upload handling combines a configured directory with a submitted filename
and exposes both a framework upload path and a direct storage API.

**Review the storage boundary.** Follow the filename through parsing, destination building,
and storage. Apply filename validation and destination containment at the write boundary
so direct callers receive the same protection. Check that supported server-configured
subdirectories and ordinary basenames retain their documented behavior.

**Regression assertions.** Save a benign multipart upload and a direct storage upload into
a temporary root and compare their final paths and contents with the expected files.
Stub the storage boundary to deny a destination and verify that the caller reports the
error without creating or replacing a file.

## Outbound discovery requests

**Applies when** a discovery client builds a URL from a supplied identifier and follows
redirects to retrieve a descriptor.

**Review the request boundary.** Validate the initial destination and every resolved
redirect against the same outbound policy before transport. Check where the client resolves
relative redirect locations and where it enforces the redirect limit and deadline.

**Regression assertions.** Use a stub transport and a controlled clock to verify that an
approved request and an approved relative redirect return the expected descriptor. Have
the policy stub deny a destination and assert that the transport receives no request for it.
Check that redirect exhaustion and an unresponsive transport terminate with the documented
errors.

## Authorization model changes

**Applies when** a versioned authorization service evaluates stored relationships against
the model selected for a request.

**Review model enforcement.** Validate stored tuples against the selected model during
evaluation, including direct tuples, userset expansion, and tuple-to-userset resolution.
Check that permission checks and object listings apply the same model restrictions when
the store still contains relationships written under an earlier version.

**Regression assertions.** Use an in-memory store with a relationship valid under an
earlier model and a second relationship still valid under both versions. Verify that the
tightened model excludes the first from both permission checks and object listings while
preserving the second. Check that explicit selection of the earlier model retains its
documented behavior.

## Packet manifest source containment

[Inspect the two indexed review steps](../cases/case-9188d8e64cc3477d9dd4e0de19623ca1/case.json).

**Applies when** a reader takes source-file references from an imported manifest and uses
them to rebuild a report from files in a packet directory.

**Review the file boundary.** Resolve references against the packet root and enforce
containment on the resolved paths before opening the inputs. Apply the same rule to each
manifest-controlled input consumed by the reader.

**Regression assertions.** Use a disposable packet with a normal input and a reference
that normalizes to another path within the packet. Verify both are accepted. Use a
temporary fixture outside the packet to verify that denied references are rejected before
reading. Compare the repaired reader's ordinary report and summary with the baseline bytes.

**Source observation.** Five targeted checks passed after the repair. The ordinary report
and summary matched the baseline byte for byte. Official grading was unavailable.

## Retention policy changes during cleanup

**Applies when** a background worker deletes records in batches while administrators can
change a workspace's retention policy.

**Review the deletion boundary.** Identify when the worker reads the policy and when it
commits each deletion. Check that an updated or cleared policy governs later batches in
the same cleanup pass.

**Regression assertions.** Pause the worker between batches in a temporary store. Change
or clear the policy, resume cleanup and verify that records retained by the current policy
survive. Use an unchanged policy as a control and verify that eligible records are removed.

## Import deduplication ownership

**Applies when** ordinary writes and imports use the same storage layer and imports need
stable identifiers to recognize previously imported records.

**Review identifier ownership.** Trace assignment and lookup of import identities. Keep
system-managed deduplication scoped to the import path and its owning workspace.

**Regression assertions.** Import the same input twice and verify that the second import
finds the original records. Verify that ordinary writes preserve their usual behavior and
cannot reserve import identities. Check that independent workspaces can import the same
input without sharing deduplication state.

## Environment-specific browser origins

**Applies when** an API serves a browser dashboard and uses different origin defaults for
development and production.

**Review origin configuration.** Trace how startup selects the default allowlist and how
an explicit setting replaces it. For routes that use browser credentials, verify that
response middleware applies the effective policy consistently.

**Regression assertions.** In an in-process HTTP fixture, compare development defaults,
production defaults and an explicit allowlist. Check the headers for allowed and denied
origins on ordinary requests and preflight requests.

## Structural limits for agent findings

[Inspect the two indexed review steps](../cases/case-87e4162558084e4588cd36b0e11c7e3e/case.json).

**Applies when** a parent process accepts a JSON findings document written by a worker
and controls how much memory may be spent validating it.

**Review the parse boundary.** Check that pre-parse limits cover the total number of
containers and object fields in addition to document size and nesting depth. Confirm that
the validator returns a structured error when a limit is exceeded.

**Regression assertions.** Use small configurable limits to check documents at and above
each threshold. Verify that accepted findings still validate and that over-budget input is
rejected before parsing. The source review confirmed the defect locally and both targeted
regressions passed on the repaired copy. The observed process crash depended on a constrained
heap.

## Read-only API inspection defaults

[Inspect the two indexed review steps](../cases/case-43ef20b41f424007a7da056226ccf9f5/case.json).

**Applies when** a tool inspects an API description and promises read-only behavior unless
the operator explicitly enables state-changing operations.

**Review the request boundary.** Check the effective policy at dispatch and trace each
entry point that shares it. Verify that default inspection respects the read-only setting
through both direct use and API-description processing.

**Regression assertions.** Use a local fixture that records received requests and maintains
disposable state. Run both entry points with default settings. Confirm that a permitted read
arrives, no write is sent, and the fixture state is unchanged. Verify policy configuration
independently of the transport. The source review confirmed the default policy defect on a
loopback fixture and verified the repaired default through both entry points.

## Uploaded figure names in storage and rendering

[Inspect the two indexed review steps](../cases/case-34aa202643cc46f683d56cbeb98877a5/case.json).

**Applies when** an upload handler saves a figure using a client-supplied name and the UI
later shows that name in a preview.

**Review both boundaries.** Enforce a safe storage name and containment at file creation.
Treat the displayed name as text and use the rendering framework's escaping for its output
context. Review each boundary where it handles the value.

**Regression assertions.** Save and display an ordinary figure using a temporary upload
directory. Check that invalid storage names are handled without writing outside the upload
root. Render a display name containing markup characters and verify that the preview shows
literal text. The source review identified separate storage and rendering defects and
reported seven passing regression tests on the repaired copy.

## Credentials across downloader redirects

[Inspect the two indexed review steps](../cases/case-aed098f3b20c4e5ab0a2376e3f549b1f/case.json).

**Applies when** a downloader attaches a credential to requests for a configured mirror
and supports several transport implementations.

**Review redirect handling.** Check credential forwarding separately for every transport.
Require the selected transport to enforce the intended origin boundary before attaching
credentials. Report unsupported authenticated configurations clearly.

**Regression assertions.** Use two disposable local HTTP fixtures and a synthetic token.
Verify that a redirect cannot deliver the token to the second origin. Check that ordinary
unauthenticated downloads still work. The source review reproduced the leak with a real
alternate downloader and verified the repaired denial and unauthenticated control. A file
permission assertion failed on both baseline and repaired copies in that environment.

## Serialization after WebSocket parsing

[Inspect the two indexed review steps](../cases/case-a99312de3fbb49aba9133e32cb5e60e7/case.json).

**Applies when** a session server parses client JSON and serializes the resulting value
again for logging or event persistence.

**Review serialization boundaries.** Account for failures in serialization even after
parsing succeeds. Handle logging and persistence failures without terminating the session
server or writing malformed records.

**Regression assertions.** In a disposable authenticated session, submit a bounded value
that exercises serialization failure. Verify that the server remains responsive and that
ordinary events still produce valid records. The source review reproduced a process exit
on the baseline and verified continued HTTP service after the repair. The three existing
targeted suites passed with 86 tests in total.

## Evaluation workspace ownership

[Inspect the two indexed review steps](../cases/case-e5155845d83d47c0b93c2d613ebacccd/case.json).

**Applies when** a local evaluation runner derives result paths from contributed case
identifiers and copies fixtures before cleaning setup directories.

**Review path construction and cleanup.** Validate identifier types before constructing
result paths and enforce result-root containment. Inspect copied directory entries without
following links before adding them to recursive cleanup operations.

**Regression assertions.** Use temporary result and fixture roots with outside sentinel
files. Verify that an invalid identifier is rejected before execution and leaves outside
files intact. Verify that cleanup of a copied fixture preserves the sentinel behind a
directory link. Use an ordinary fixture and valid identifier as controls. The source review
confirmed both boundary failures locally and verified sentinel preservation after repair.

## Network addresses used by image embedding

[Inspect the two indexed review steps](../cases/case-0d34116e46c14e2d98cc41d617d17ab6/case.json).

**Applies when** an HTML extraction tool fetches images from supplied URLs and intends
to permit public network destinations only.

**Review the connection boundary.** Classify resolved addresses, including mapped address
forms, and ensure that the connection uses an address that passed validation. Apply the
same policy to every destination reached during fetching.

**Regression assertions.** Use controlled resolution and disposable HTTP fixtures to
verify denied-address handling and the documented fallback image. Confirm that an allowed
image remains embeddable. Check that a second resolution cannot change the destination
between validation and connection. The source review confirmed two address-validation
gaps through the real CLI and tested a repair that pins the validated socket address.

## Agent hook write policy and audit integrity

[Inspect the two indexed review steps](../cases/case-02f334389f374041a4f294bb3cab066f/case.json).

**Applies when** agent hooks classify proposed writes by directory and record agent metadata
in a line-oriented audit log.

**Review the write policy.** Normalize path components before applying directory rules,
including for new files whose intermediate directories do not exist. Trace the normalized
path through the actual hook entry point to the warning shown to the user.

**Review the logging sink.** Keep supplied agent and session values from creating additional
records or fields. Check invocation and completion hooks with each supported input parser.

**Regression assertions.** Use a temporary project to compare equivalent path spellings,
protected configuration paths and allowed new artifacts. In a temporary audit log, compare
record and field counts for separator-bearing metadata and ordinary names. The source
review reproduced both defects before repair. Fourteen repaired checks passed with the
primary and fallback parsers. The path repair covers lexical normalization in an advisory
guard. Symlink handling and absolute paths outside the project remain unresolved.

## Read-only filesystem browser containment

Use identical mount boundary checks for direct file access, directory listings and content
search. Check resolved entry targets during recursive walks, and use ordinary in-mount
files as controls for each operation. The source review ran the generated scripts locally.
The repaired module passed all 16 tests on a fresh working copy. The separate bridge
service and live remote transport were outside the executed checks.

[Inspect the two indexed review steps](../cases/case-59b8970214cf462c99cdddc262e449e8/case.json).
