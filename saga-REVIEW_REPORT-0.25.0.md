# Saga 0.25.0 source review report

## Scope

This review covered the Saga 0.24.1 baseline plus the 0.25 platform qualification work: Python reference runtime/CLI, independent Go Native implementation, Hosted adapters, mobile generation, registry/package handling, Vulkan qualification, CI/device-lab gates, SH-3 qualification evidence and GA-readiness tooling.

The review focused on capability boundaries, fail-closed behavior, stale evidence, generated-project correctness, package identity/rollback, current-release qualification reproducibility and cross-implementation consistency.

## Findings corrected

### High — physical GPIO lacked a dedicated authority boundary

GPIO can change real electrical outputs, but the Hosted adapter could be reached without a device-specific capability. Added `Capabilities.allow_device`, `require_device()` and CLI `--allow-device`; all GPIO operations now fail closed without the grant.

### High — Spark could indirectly spawn Java/Py4J without process authority

Creating a Spark session launches external processes. `spark.session` and `spark.local_session` now require `--allow-process`, preventing the Spark adapter from bypassing the normal process capability.

### High — generated Android/iOS StandardCoreRuntime was incomplete

The mobile generator copied an incomplete subset of the Go Native runtime, leaving symbols such as process/toolchain helpers, source loading, number conversion, class derivation and native/FFI boundaries unresolved. The generator now includes the required pure Standard Core dependencies and a deliberately fail-closed mobile support boundary for compiler/FFI/JIT/host-only operations. Generated Android and iOS runtimes build, vet and execute embedded Saga source in regression tests.

### High — registry install trusted archive transport identity more than package identity

A registry response could contain a package whose internal `saga.toml`/`saga.lock` identity differed from the requested name/version. Install now validates internal project and lock identity, verifies the lock, stages extraction, preserves an existing valid target on failure and uses atomic dependency-lock replacement.

### Medium/high — Android project generator emitted an invalid build script

Generated `app/build.gradle.kts` had an unmatched Android block. The generator was repaired and regression checks now require balanced generated Kotlin DSL plus a buildable StandardCoreRuntime. Android toolchain values were refreshed in the 0.25 generator/CI profile.

### Medium — generic AWS adapter could address private SDK methods

`cloud.call` now accepts public identifier-shaped method names only and rejects underscore/private/internal method names before SDK dispatch.

### Medium — current-release qualification could reuse stale evidence

The original GA logic could find older cross-implementation evidence. The gate now requires exact `0.25.0` evidence, and `tools/cross_implementation_validation.py` executes the current Python reference and current independent Go Native implementation against the same corpus.

### Medium — Python conformance metadata reported an obsolete implementation version

Python `conformance --json` reported `0.9`. It now reports implementation `0.25.0` and the active Language Edition metadata.

### Medium — SH-3 0.25 release corpus files were omitted during the version bump

The 0.25 validator expected current-release Standard Core and Edition 2027 corpus manifests that were not packaged. Current-release corpus files were added and split SH-3 qualification was rerun.

### Medium — standalone qualification tools depended on ambient `PYTHONPATH`

`cross_implementation_validation.py` and `registry_live_qualification.py` imported `saga` before adding the project root. Both now establish their own source root and launch correctly from unrelated working directories; regression coverage invokes their `--help` entry points without ambient `PYTHONPATH`.

### Medium — GA audit parser crashed on the real audit JSON shape

`ga_readiness.py` attempted `int(issues)` while the internal audit stores `issues` as a list. The gate now handles list and numeric representations safely and fails closed on malformed evidence.

### Medium — HTTP server response ACK could lose a race with request-context cancellation

Final candidate ZIP Race Detector verification reproduced a false `request closed while writing response` result after a successful response write. `net/http` cancels the request context as a handler returns, so the context and the buffered write acknowledgement can become ready together. The response path now deterministically prefers an already-buffered write acknowledgement, while still reporting a real close when no acknowledgement exists. A direct simultaneous-ready regression was added and the Go suite/Race Detector were rerun.

### Medium — Python reference distribution lacked a normal module entry point and debugger command

Added `saga/__main__.py`, so `python -m saga` maps to the canonical CLI. Added a statement-level Python debugger with `--trace` and repeated `--break LINE`, capability-aware execution and regression tests, closing a workflow asymmetry with Saga Native.

### Medium — Language Specification RC1 had duplicate/out-of-order normative clauses

RC1 contained duplicate 21–27 numbering after clause 30, annexes in the middle of the numbered clauses and a duplicated sentence. A reorganized 1.0 RC2 candidate was produced with unique monotonic clauses 1–37 and annexes moved to the end. It remains RC rather than being promoted to Final without independent review.

### Low/CI — mobile workflow referenced a nonexistent example

The workflow referenced `examples/learning/01_hello.saga`; it now uses the existing `01_foundation.saga`.

### Low/CI — Vulkan Xvfb qualification used a fixed display number

The qualifier now selects a free display in the configured range, avoiding parallel-CI collisions.

## Review result

No unresolved critical/high issue found by the project-internal review remains in the changed source areas. Automated internal security audit reports zero issues. This is not an independent penetration test or security certification.

External evidence remains intentionally unresolved where this host cannot supply it: physical GPU/gamepad/GPIO, authorized live AWS, real pygame/Spark packages on this host, Android/iOS devices, native Windows/macOS execution, live external HTTPS registry and independent third-party audit.
