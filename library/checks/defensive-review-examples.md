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
