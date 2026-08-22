# Saga 0.22.0 Source Review Report

## Objective

Broaden Saga's application API surface toward common browser operations and convert the previous browser-runtime simulation evidence into an actual Chromium Blink/V8 execution result without weakening SH-3, capability safety or managed-host policy.

## Defects found and repaired

1. **Browser SH-3 did not consume the `edition 2027` source directive.** The Go checker accepted the directive, but the canonical browser kernel treated `edition` as an ordinary name and could emit `SAGA-T102`. The canonical kernel now consumes/validates Edition directives before execution/lowering.
2. **Self-host bootstrap compiler did not consume the Edition directive.** Empty-PATH `sagac` could therefore reject source that the full checker accepted. `sh3c.saga` now accepts the supported directive and fixed-point hashes were regenerated.
3. **Generic browser event binding broke minimal host/test doubles.** `addEventListener` is used where available, with `on<event>` fallback for constrained hosts.
4. **`on_click` compatibility drift.** The expanded event metadata initially changed the old click-dispatch shape. The dedicated API preserves the historical shape while `on_event` provides richer metadata.
5. **Capability probing could throw on opaque origins.** Direct localStorage property access can throw `SecurityError`; feature discovery now uses guarded access and reports unavailable capabilities instead.
6. **Chromium validation originally depended on top-level local navigation.** The host's managed `URLBlocklist=["*"]` blocks such navigation. The test was redesigned to execute the real browser engine through CDP on `about:blank` without modifying or evading the policy; origin-required features are not overclaimed.

## API architecture review

Adding a dedicated Saga function for every possible DOM event, CSS property, HTTP method or browser vendor API would be unmaintainable and would make the language surface noisy. 0.22 therefore combines typed high-level APIs with generalized primitives:

- `on_event` for arbitrary event names;
- `set_attr` / `set_style` for extensible DOM properties;
- generic Fetch request parameters;
- WebSocket operations;
- capability queries and fail-closed permission boundaries.

The release manifest contains 101 Browser Host operations and six pure web helpers, for 107 typed `web` functions. A machine validator ensures the manifest/checker/kernel/host surfaces stay aligned.

## Result

The review found no unresolved functional defect in the release gates described by `saga-VALIDATION-0.22.0.md`. Real Chromium execution is now PASS for the tested Blink/V8 Saga path. Managed host policy is preserved, so service-worker/offline navigation is deliberately not marked Chromium-PASS in this environment.
