# Saga General Availability 1.0 readiness contract

Saga must not call itself a generally available, standard-use language merely because a large test suite passes.  The project uses two explicit levels.

## Core GA 1.0 — “標準的に使える”

All mandatory gates must be independently evidenced:

1. **Language Specification 1.0 Final** — the exact proposed-Final bytes and normative grammar are approved by an independent reviewer, the signed review attestation verifies, and the project promotion tool materializes the Final document from those reviewed bytes.
2. **Compiler/runtime conformance** — Python reference, Saga Native and SH-3 qualification pass, including fixed-point self hosting, race tests and fuzzing.
3. **Independent second implementation** — cross-implementation conformance remains green.
4. **Desktop host releases** — the same source-manifest-bound release is built and executed on Linux, Windows and macOS native operating-system hosts; cross-build format checks do not count. Hosted-VM evidence is labeled as such and is not mislabeled physical hardware.
5. **Package ecosystem path** — a globally reachable, CA-validated HTTPS Registry Protocol v1 endpoint passes signed Python↔Go publish/search/install, explicit publisher trust, immutable-version rejection, reproducible lock data and documented recovery/rotation procedures.
6. **Security evidence** — no unresolved project-internal critical/high findings and an independent third-party audit report plus Ed25519 attestation are bound to the exact release source-manifest/report hashes, cover the mandatory scope/methods, and have zero open critical/high findings.
7. **Developer workflow** — formatter, linter, tests, LSP, debugger/diagnostics, package tooling and migration/compatibility documentation are release-qualified.

Only when every item above is PASS may `ga_ready` become true.

## Full platform qualification

These are valuable official profiles but are not blockers for the core language to be generally usable: Vulkan physical GPU, physical gamepad, AWS live account, physical GPIO, real Spark runtime, real pygame runtime, Android device and iOS device.  Each profile has its own live evidence gate and must never inherit PASS from a mock, cross-build, simulator, software renderer or API stub unless the evidence explicitly names that class.

ISO/IEC standardization is separate.  Saga GA 1.0 would mean the project considers the language stable for ordinary production use; it would **not** mean ISO/IEC has approved Saga.
