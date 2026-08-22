# Saga 0.26.1 review-hardening release notes

## Theme: evidence-chain and Registry hardening for independent review

Saga 0.26.1 is a patch release of the 0.26 independent-review candidate. A second source review found weaknesses that did not invalidate the language core but could weaken reviewer reproducibility, package-registry safety or the integrity of evidence used by the Core GA 1.0 gate. Those weaknesses are corrected here and covered by regression tests.

0.26.1 is still **not Core GA 1.0**. Independent specification approval, current-source native Windows/macOS execution, a live public verified-HTTPS Registry run and an independent signed security audit remain external evidence requirements.

## Evidence and source-identity hardening

- `tools/ga_readiness.py` no longer accepts a current-release evidence file merely because it says `pass: true`. Evidence must bind to the exact current `release/source-manifest-0.26.1.json` SHA-256 and exact source-tree SHA-256, and each gate rechecks its required named qualifications.
- Source-manifest verification now rejects malformed or duplicate records, unexpected symlinks and tree/digest mismatches before evidence is accepted.
- Native-host evidence records and rechecks host identity, executable SHA-256, executable format and the complete required target-host qualification set.
- External security evidence is bound to both the exact reviewed source manifest and exact audit-report SHA-256; Critical/High open findings fail closed.
- The generated `SAGA_LANGUAGE_SPECIFICATION_1.0.md` is intentionally not part of the pre-review source manifest because it is produced only after independent approval. The Final candidate, grammar and promotion implementation remain source-bound, while GA independently requires the generated Final bytes to equal the reviewer-signed `proposed_final_sha256`. This removes the previous circular condition in which legitimate Final promotion could invalidate the frozen source manifest.
- `tools/go_race_qualification.py` enumerates the complete Go test set and supports split Race Detector qualification. Reviewer/preflight command capture uses temporary files rather than inherited pipes so grandchildren cannot keep a capture pipe open after the tested process exits.

## Registry Protocol v1 hardening

- Python Registry HTTP access disables ambient proxy inheritance and automatic redirects. Non-loopback Registry URLs must use HTTPS; URL userinfo/query/fragment components are rejected.
- Registry publisher bearer tokens are no longer stored in plaintext. The server persists only a SHA-256 verifier in a mode-0600 atomic configuration file on POSIX and migrates legacy plaintext configurations when loaded.
- Python and Go Registry key generation is create-only: an existing private/public key path or symlink is refused rather than overwritten. Private keys use restrictive permissions.
- Python and Go both validate archive paths, duplicate entries, symlinks/special files, compressed/expanded resource bounds, `saga.toml`/`Saga.lock` identity and the complete lock snapshot before installation.
- Duplicate JSON object keys in `Saga.lock` and duplicate relevant TOML identity keys are rejected instead of being silently resolved by parser order.
- Go installation now performs the same full lock verification after staging that the Python implementation performs.
- Stored packages are revalidated before search/download and before an immutable same-version publish is treated as idempotent. A corrupted stored package/signature can no longer yield a false successful retry.
- The public live qualification creates unique package identities per run so it can be repeated without conflicting with immutable-version policy.
- Live HTTPS evidence resolves candidate addresses, connects to a globally routable resolved address with verified TLS/SNI and records the actual peer address. Merely having one global address in DNS is insufficient.
- The old Go backend per-`RemoteAddr` limiter was removed because the canonical reverse-proxy deployment made all users appear as the ingress address and could turn the limit into a registry-wide bottleneck. Resource, authentication, signature and timeout limits remain in the backend; abuse/rate policy belongs at a trusted ingress that has authoritative client identity.
- Registry Protocol v1 remains singular across Python and Go: `PUT/GET /v1/packages/{name}/{version}` and `GET /v1/search`; legacy Go Registry endpoints remain HTTP 410.

## Release/reviewer reproducibility fixes

- Current 0.26.1 compatibility manifests are present under the filenames consumed by the 0.26.1 validators.
- The public release packager now includes the Language Specification 1.0 Final Candidate, normative EBNF and review handoff instead of packaging obsolete draft specification material.
- The current SH-3 Standard Core and Edition 2027 qualification corpora are authoritative under `conformance/sh3/`, which is source-manifest-bound. Validation output remains separate from qualification input.
- The public HTTPS Registry qualification is rerunnable and source-bound.
- Hosted GitHub workflows use current supported major versions selected for the hosted runners; self-hosted hardware-lab workflows remain separately compatibility-managed.
- Re-review corrected an earlier review note: the Registry Docker image executes the Go Native Saga CLI, and its `registry serve --addr ...` form is a valid Go CLI contract. The Docker `--addr` use is therefore **not** recorded as a defect in 0.26.1.

## Validation summary

On the current Linux validation host:

- Python regression: **195/195 PASS** plus the existing four subtests.
- Go Native full tests: **PASS**.
- `go vet ./...`: **PASS**.
- `sagaffi`, `sagajit`, combined FFI+JIT, `sagadesktop` and `sagadesktop+sagavulkan` tagged suites: **PASS**.
- Go Race Detector: **87/87 named tests PASS** when executed in bounded split groups; the monolithic run exceeding the outer harness window is not counted as a PASS.
- Hosted API: **168/168 PASS** across 28 modules.
- Registry Protocol v1 Python↔Go interoperability: **8/8 PASS**.
- Python↔Go language differential conformance: **13/13 PASS**.
- Security, Native Game, Browser Host and Universal App validators: **PASS**.
- Real Chromium 144 Blink/V8 integration: **PASS**.
- Parser fuzz: **100,000 cases**, unexpected host exceptions 0.
- Expression fuzz: **25,000 cases**, unexpected host exceptions 0.
- SH-3 compiler Stage2/Stage3 fixed point: **PASS**; compiler SHA-256 `8ea80749c7aba49116742de76cca0168c8b37357fb27b3cbdd000a0739ab12d4`.
- SH-3 canonical kernel Stage2/Stage3 fixed point: **PASS**; kernel SHA-256 `a044627a6abde1783bcece40ffa976f72d129a0cf31538d06b62162c4dce4237`.
- SH-3 Standard Core **23/23**, diagnostics **11/11**, Edition 2027 **15/15**, deterministic image, empty-PATH self-host execution and source-boundary audit: **PASS**.

## GA status

`tools/ga_readiness.py` remains fail-closed. The implementation can prepare and validate the evidence, but this release does not fabricate the remaining independent/external PASSes. The remaining mandatory external tracks are:

1. independent approval of the exact Language Specification 1.0 proposed-Final bytes;
2. Windows and macOS target-host qualification for this exact source manifest;
3. a non-local, globally routable, verified-HTTPS Registry Protocol v1 live qualification;
4. an independent signed security review with zero open Critical/High findings.
