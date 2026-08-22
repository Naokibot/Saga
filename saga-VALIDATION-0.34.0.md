# Saga 0.34.0 Validation Report

## Final measured results

- Python non-platform regression inventory: **369 / 369 PASS** across 32 test modules.
- Platform/Evidence regression inventory: **9 / 9 PASS**.
- Combined Python regression inventory: **378 / 378 PASS**.
- Native Aggregate/GC dedicated regression: **13 / 13 PASS**.
- Python Self Conformance: **48 / 48 PASS**.
- Go Self Conformance: **48 / 48 PASS**.
- Python ↔ Go differential conformance: **48 / 48 PASS**.
- Module graph conformance, including payload-tagged SMI parity: **14 / 14 PASS**.
- Native Aggregate/GC qualification: **12 / 12 PASS**.
- Parser fuzz: **100,000 cases**.
- Expression fuzz: **25,000 cases**.
- Unexpected host exceptions in fuzzing: **0**.
- Go `go test ./...`: PASS.
- Hosted API validation and current API compatibility validators: PASS.
- Specification review lint: PASS.
- Internal security audit: PASS with 0 issues.

The Platform/Evidence inventory is source-manifest-bound. It passed against the release candidate tree and is rerun once more after the final source manifest is regenerated.

## Direct-native aggregate evidence

Qualification exercises real native compilation and execution for enums, lists, maps, sets, class instances, constructors, methods, cross-module calls, incremental cache behavior, GC tracing, allocator statistics, and fail-closed unsupported layouts.

A C harness verifies that a `SagaTagged` root containing a `SagaRef` payload keeps the referenced object alive across collection and that clearing the payload permits reclamation.

## Evidence boundary

The physically exercised direct-native host for this review is the available Linux/Clang environment. Cross-platform code paths do not substitute for Windows/macOS physical qualification.

## Follow-up validation — 2026-08-16

The original results above describe the first frozen 0.34 tree. After the follow-up fixes, the affected paths were revalidated rather than treating the old source-bound evidence as proof for modified code.

- Native Aggregate/GC regression, including the new C ABI fail-closed cases: **14 / 14 PASS**.
- Native Aggregate/GC qualification: **12 / 12 PASS**.
- Module graph conformance: **14 / 14 PASS**.
- Core language + Natural language targeted regression: **52 / 52 PASS**.
- Independent Go implementation: `go test ./...` **PASS**.
- Installer source profile: `go test ./...` **PASS**.
- Installer embedded-payload profile: `go test -tags saga_installer_payload ./...` **PASS** with a generated payload.
- Linux x86-64 `sagaruntime` build: **PASS**.
- Linux x86-64 offline installer built with real Saga Native/runtime payloads, `--check-only`: **PASS**.
- Linux x86-64 fresh-prefix installation, post-install Saga Native version check, native conformance check and self-host compiler bootstrap/fixed-point sequence: **PASS**.

The complete historical 378-test result is not relabeled as a new full-suite result merely because targeted post-fix tests pass. Windows/macOS physical qualification and the remaining 0.34 preview limitations are unchanged.

