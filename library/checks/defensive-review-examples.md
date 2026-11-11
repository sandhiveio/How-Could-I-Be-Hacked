# Defensive review examples

Each example states what to inspect in an implementation and what to assert in regression
tests after a repair. The expected results are acceptance criteria for the code under review.

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
