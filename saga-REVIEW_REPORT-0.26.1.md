# Saga 0.26.1 second source review report

## Scope

This is a second review of the distributed 0.26 review candidate. The review emphasized evidence-chain integrity, Registry authentication and malformed-input handling, package immutability/corruption behavior, Windows/macOS qualification trust, specification-Final promotion semantics, SH-3 qualification reproducibility and release packaging. Language/runtime regressions affected by the changes were rerun.

## Findings discovered and corrected

### High — GA evidence could be accepted without fully re-binding it to the current source tree

Several gates had strong evidence generators but the final GA aggregator did not consistently revalidate every evidence file against both the current source-manifest SHA-256 and current tree SHA-256 plus the complete mandatory check set. A stale or structurally incomplete current-release JSON could therefore be trusted too much. The GA gate now verifies current source identity first and then applies gate-specific source binding and mandatory-check validation. Native-host, live Registry, internal audit and external audit evidence are fail-closed on source mismatch.

### High — legitimate specification Final promotion conflicted with frozen-source verification

Independent approval creates `SAGA_LANGUAGE_SPECIFICATION_1.0.md` after the review candidate is frozen. If that generated Final file were treated as an ordinary new source file, the exact-tree source-manifest check would necessarily fail immediately after valid promotion, making GA unreachable. The generated Final document is now the one narrowly defined post-review artifact excluded from the candidate source manifest. The candidate, normative EBNF and promotion implementation remain source-bound, while GA independently requires the Final bytes to hash exactly to the reviewer-signed `proposed_final_sha256`.

### High — Registry publisher bearer token was stored in plaintext

The Python Registry configuration previously persisted the publisher bearer token itself. It now persists only `token_sha256`; token checking uses a hashed verifier and constant-time comparison behavior. Configuration is written through a unique temporary file and atomic replace and is mode 0600 on POSIX. Legacy plaintext configuration is migrated to the hashed form when loaded.

### High — package installation verification differed between Python and Go

Go Registry installation validated package identity/signature but did not perform the same complete staged `Saga.lock` snapshot verification as Python. A correctly signed archive containing source that no longer matched its lock snapshot could therefore be treated differently by the two implementations. Go now runs full staged lock verification. Regression coverage includes a validly signed package with a stale lock and duplicate lock JSON keys.

### Medium/high — source-manifest verification needed stronger self-integrity rules

The source identity file is itself a security boundary. Verification now rejects duplicate/malformed path records, unexpected symlinks, record/digest inconsistencies and a tree that differs from the recorded exact file set. Current SH-3 qualification inputs have also been moved under `conformance/sh3/` so they are part of that frozen source identity rather than being stored only beside validation output.

### Medium/high — Registry stored corruption could be mistaken for idempotent publication

Immutable same-version publication is intentionally idempotent only when the already-stored package and signature are still the expected valid object. Both implementations now re-read within bounds and revalidate the stored package identity/signature before returning success. Search/download also revalidate persisted material. Corrupted storage therefore fails rather than producing a false successful retry.

### Medium/high — Registry key generation could overwrite existing paths

Publisher private/public key generation previously allowed replacement of an existing target in some paths. Python and Go key generation is now exclusive/create-only and fails closed if either target exists, including symlink cases. Private key files retain restrictive permissions and partial failures are cleaned up.

### Medium — Python Registry HTTP transport inherited ambient behavior

The Python client could inherit environment proxy configuration and standard redirect following. Registry transport now disables ambient proxy use and automatic redirects. Non-loopback Registry base URLs require HTTPS, and credentials/query/fragment in the base URL are rejected. Response sizes remain bounded and system CA/hostname verification remains enabled.

### Medium — live Registry qualification was not safely repeatable

The qualifier originally reused an immutable package identity while generating new signing material, so a legitimate second run would be rejected by the immutability protection. Every qualification run now uses a unique safe run identifier/package name while still testing same-version immutability inside that run.

### Medium — DNS evidence did not prove the actual TLS peer was public

It was insufficient to show that a hostname had at least one globally routable DNS answer if a different private address could actually be selected. The live qualifier now selects a globally routable resolved address, connects directly to that address while retaining SNI/hostname verification, records the connected peer and requires the actual peer address to be global.

### Medium — backend IP rate limiting was incorrect behind the canonical reverse proxy

The Go server used `RemoteAddr` for a per-IP limiter. Behind the documented Caddy reverse proxy, ordinary clients share the ingress source address, effectively making the limit global and allowing normal traffic to block unrelated users. That misleading backend limiter was removed. Body/header/timeouts, authorization, signature and immutability protections remain backend responsibilities; client-aware abuse/rate policy belongs at a trusted ingress with authoritative client identity.

### Medium — current compatibility-manifest filenames were missing after the patch release bump

0.26.1 validators referenced 0.26.1 compatibility filenames while only the older release-named files were present. The current manifests were restored with the unchanged compatible API surface and current release metadata.

### Medium — public release packaging retained obsolete draft specification material

The release packager now includes the Language Specification 1.0 Final Candidate, normative EBNF, review handoff and current qualification documents instead of treating obsolete DRAFT material as the current specification payload.

### Medium — Race qualification output capture could remain open after the tested process exited

Some Go tests spawn children/grandchildren. Capturing a child with a Python pipe can leave the pipe descriptor inherited by a descendant, making the qualifier wait for EOF even though `go test` itself has completed. Reviewer preflight and split Race qualification now capture via temporary files, removing that inherited-pipe lifetime dependency.

### Medium — wrong-host qualification performed unnecessary work before refusing

`native_host_qualification.py --expected-host windows` on Linux eventually failed, but only after costly unrelated checks. Host mismatch is now an immediate fail-closed decision.

### Re-review correction — Docker `--addr` was not a defect

An earlier review note treated the Registry Docker `--addr` option as if it were invoking the Python CLI. The image executes the Go Native Saga CLI, whose Registry server command validly accepts `--addr`. The re-review therefore removes that earlier defect classification rather than perpetuating it.

## Defensive review observations

- Registry Protocol v1 remains one signed protocol across Python and Go; legacy Go endpoints return HTTP 410.
- Archive parsing rejects absolute/traversal/backslash/NUL/duplicate paths, symlinks/special files and excessive compressed/expanded resources.
- Duplicate relevant identity keys are rejected rather than silently taking a parser-defined last value.
- External-security evidence verifies exact report bytes and exact current source identity and refuses open Critical/High findings.
- Final specification promotion still requires an independent Ed25519 approval over exact candidate/grammar/proposed-Final hashes.
- Cross-build formats do not satisfy Windows/macOS target-host execution gates.

## Validation after corrections

- Python: **195/195 PASS** plus four subtests.
- Go full regression: **PASS**.
- Go vet: **PASS**.
- FFI/JIT/Desktop/Vulkan tagged Go regression profiles: **PASS**.
- Go Race Detector: **87/87 named tests PASS** in bounded split execution; the monolithic outer-harness timeout is not counted as a PASS.
- Hosted API: **168/168 PASS**.
- Registry Python↔Go interoperability: **8/8 PASS**.
- Python↔Go language differential conformance: **13/13 PASS**.
- Security/Game/Web/App validators, machine smoke, real Chromium 144, parser/expression fuzzing and internal automated security audit: **PASS**.
- SH-3 compiler and canonical-kernel Stage2/Stage3 fixed points, Standard Core 23/23, diagnostics 11/11, Edition 2027 15/15, deterministic image, empty-PATH self-host execution and source-boundary audit: **PASS**.

## Assessment

No unresolved project-internal defect found by this second review remains in the changed areas. This is not a proof of absence of defects and is not the required independent third-party review. The four externally sourced Core GA evidence tracks remain deliberately blocked until their actual artifacts verify against the final 0.26.1 source manifest.
