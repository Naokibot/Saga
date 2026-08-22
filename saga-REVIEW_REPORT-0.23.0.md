# Saga 0.23.0 review report

## Objective

Make application behavior open-endedly expressible from Saga source without requiring another application language, while preserving type checking, explicit capability boundaries, SH-3 self-hosting and fail-closed behavior.

## Defects found and corrected

1. **Checker/runtime import mismatch.** `use web` and `use embedded` were accepted by the checker but absent from the Native runtime `UseStmt` allowlist, causing `SAGA-R120` before module-specific fail-closed handling. Runtime import dispatch now matches the checker and includes the new `app` module.
2. **Browser UUID advertised-but-not-runnable mismatch.** The browser manifest exposed `crypto.random_uuid`, but Chromium `about:blank` can lack `crypto.randomUUID()` because it is not a secure context. Added RFC 4122 v4 generation using `crypto.getRandomValues()` when available.
3. **Media constraint narrowness.** Browser media capture forwarding previously assumed boolean audio/video flags. It now preserves structured constraints as well.
4. **Extensibility without unsafe eval.** Rather than adding `eval`/raw JavaScript to claim universal coverage, the `app` protocol uses operation identifiers plus JSON and a host-adapter registry. Unknown/unavailable actions are errors.

## Security/architecture decisions

- Capability discovery and actual operation success are separate; permission or hardware absence can still reject after discovery.
- Native `process.run` is argv-only and does not implicitly invoke a shell.
- Native HTTP helper is bounded; filesystem actions validate object-shaped JSON payloads.
- Browser Universal App actions do not provide a generic JavaScript-eval escape hatch.
- Proprietary actions may use vendor namespaces, but their adapters are outside conformance until independently implemented/tested.

## Result

No unresolved project-internal automated review findings remain. Go test/vet/race, Python regression, game/web/app API validators, fuzzing, real Chromium integration and split SH-3 qualification pass. Device/service-specific hardware validation remains explicitly unclaimed.
