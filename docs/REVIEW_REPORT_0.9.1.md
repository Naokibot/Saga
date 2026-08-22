# Saga 0.10.0 source review report

Date: 2026-08-07
Scope: Saga 0.9.0 Python reference implementation, Go PCL1 implementation, standard library, packaging, diagnostics, concurrency boundaries, network adapters, and release metadata.

## Summary

Saga 0.10.0 is a corrective patch for the Saga 0.9 language edition. The review reproduced multiple defects that were not covered by the 0.9.0 baseline suite and fixed them with regression tests.

## Findings and resolutions

| Severity | Finding | Resolution |
|---|---|---|
| High | Isolated thread tasks deep-copied global Saga instances. Their class/function graph could include host executor locks, causing `cannot pickle '_thread.RLock' object` and violating the intended class-world remapping. | `Interpreter.fork()` now snapshots globals through `_snapshot_value_to`, remapping Saga instances to classes owned by the forked interpreter. Added isolation regression test. |
| High | `private` fields were hidden from reflection and JSON but leaked through `print(object)` and `text(object)`. | Standard display now omits private fields. Added regression test checking the secret never appears. |
| High | WebSocket client inherited host proxy environment and followed redirects inside `websocket-client` without re-running Saga network capability checks. | Ambient proxy use is disabled (`http_no_proxy=['*']`), automatic redirects are disabled, and redirect handshakes are rejected with an explicit error. |
| Medium | Python accepted Unicode decimal digits such as Arabic-Indic `١٢٣` as numeric literals while the Go implementation could not parse them. | Saga 0.9 numeric literals are explicitly ASCII `0`-`9`; Python and Go lexers now reject non-ASCII numeric digits. Added PCL1 case C014. |
| Medium | `process.run` retained a hard-coded 16 MiB post-capture output rejection from pre-0.8 behavior, contradicting the no-fixed-normative-ceiling model. | Removed the Saga-specific 16 MiB ceiling. Host memory/OS policy remains the resource boundary. Added a 17 MiB regression test. |
| Medium | Canonical `.sagapkg` used DEFLATE. Equal inputs can produce different bytes across zlib implementations, weakening cross-platform reproducibility claims. | Canonical package members now use ZIP method 0 (`STORED`), while member order/time/mode remain fixed. |
| Medium | Several detailed diagnostics were derived by matching Japanese message text, so wording edits could change machine-readable IDs. | `SourceError` and `NativeFailure` now support explicit detailed diagnostic IDs. Conformance-critical lexical, parsing, typing, capability, bounds, division, option and assertion paths now pass IDs directly. Legacy generic paths keep compatibility fallback. |
| Low | Patch-version metadata was inconsistent across CLI, LSP, templates, build scripts, conformance tooling and installer sources. | Release metadata synchronized to implementation 0.10.0 while keeping language edition 0.9. |

## Compatibility

The source language edition remains `0.9`. This patch tightens previously ambiguous numeric literal behavior by specifying ASCII numeric digits. Programs that used non-ASCII Unicode decimal digits as source numeric literals were accepted only by the Python implementation and were already non-portable to the independent Go implementation; they must be rewritten with ASCII digits.

The `.sagapkg` byte format changes because canonical members are now stored rather than deflated. `saga.lock` schema remains 1 and source semantics do not change.

## Residual risks

- The Go implementation remains Portable Core Level 1, not a complete independent Standard Core implementation.
- Python plugins are trusted native code after `--allow-plugin`; Saga does not sandbox arbitrary Python code inside the process.
- Cloud SDKs are also explicit trust boundaries and may perform provider-specific credential/network discovery.
- Capability path checks reduce ambient authority but cannot eliminate OS-level TOCTOU races without an OS sandbox or descriptor-relative filesystem API.
- No-fixed-normative-ceiling means very large process output, HTTP bodies, precision, worker counts, etc. can exhaust host resources. Production deployments should apply OS/container quotas or optional watchdog policy.
- Legacy/non-profile diagnostics may still use the compatibility classifier until all generic diagnostics receive dedicated IDs.

