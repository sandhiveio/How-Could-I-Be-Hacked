# Reusable check: static-file path containment

Use this checklist when a handler derives a filesystem target from an attacker-controlled URL
pathname and serves it from a configured content root. It is derived from an executed,
anonymous source case; retest every item against the new target rather than treating it as
already proven.

## Trust boundary

- Identify the exact point where the request pathname becomes a filesystem path.
- Identify every mutation after that point, especially appending a default index filename,
  decoding, separator normalization, and file-existence checks.
- Confirm whether the configured root is absolute at request time and whether it is re-resolved
  per request.

## 1. Reproduce before repairing

Use a disposable fixture with:

- a root index file, an ordinary file, and a nested file;
- a missing path and an extensionless directory without an index;
- a sibling file outside the root and a sibling directory outside the root whose index file
  carries harmless marker bytes;
- a handler on an ephemeral loopback port.

Send raw request shapes without client-side normalization: single parent traversal, deep
traversal, doubled-slash traversal, extensionless traversal to the sibling directory, and
ordinary controls. Record status, content type, body hash, and marker presence for every case.

## 2. Characterize the parser

- Test literal parent-directory segments first; they are the baseline.
- Test percent-encoded dot segments, encoded separators, mixed separators, and a trailing
  encoded null. Some parsers leave these undecoded and therefore inert; record that rather
  than assuming they leak.
- Test absolute-looking and doubled-slash forms.
- Test query strings to confirm the gate sees only the pathname.

## 3. Minimal repair

After the join and **before** any conditional append:

1. Resolve the configured root.
2. Resolve the joined target.
3. Accept only when the target equals the root or begins with the root plus the path
   separator.
4. Otherwise return the handler's existing not-found page.

This admits the root itself and rejects sibling paths that merely share a name prefix. Do not
add decoding unless the parser test showed a decoded leak; a decoding layer broadens behavior
and should be justified by an observation.

## 4. Regression and differential evidence

Run the same suite against a vulnerable copy and a patched copy:

- Ordinary files and nested files must return 200 with body hashes matching the source files.
- Directory index behavior must be unchanged.
- Missing paths and extensionless directories without an index must remain 404.
- Every traversal shape must return 404 with zero marker bytes.
- Encoded shapes must preserve their pre-fix behavior (inert stays inert).
- A sibling path sharing a long name prefix must be rejected.
- A relative root under a changed working directory must still contain the target.
- Parallel leak and control requests must not mix status or content.

The suite is discriminating only if the vulnerable copy fails exactly the leak cases and the
patched copy passes all cases. Save both result sets.

## 5. Bound the limitation

Measure, do not assume, symlink behavior:

- A symlink inside the root pointing outside may pass a string-prefix check.
- A directory symlink and a file symlink may behave differently because of the append branch.
- Decide explicitly between documenting the limitation and adding realpath hardening. A
  realpath repair can change legitimate in-root symlink serving, so record the trade-off.

Package the repair as a unified diff and, when the harness requires it, a machine-readable
patch record. A local suite is evidence, not an official benchmark pass; run the official
harness separately and cite its output.
