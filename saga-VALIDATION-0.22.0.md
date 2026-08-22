# Saga 0.22.0 Validation Report

Validation host: Linux x86-64. Primary scope: Browser/API Expansion, actual Chromium execution, and preservation of the official SH-3 qualification.

## Core regression

| Check | Result |
|---|---:|
| Go reference `go test ./...` | PASS |
| Go `vet ./...` | PASS |
| Go Race Detector | PASS |
| Python reference | **155/155 PASS + 4 subtests** |
| Native game checker/runtime/manifest | **101/101 aligned** |
| Browser Host API checker/kernel/host manifest | **101/101 PASS** |
| Internal automated security review | PASS, 0 unresolved findings |
| Parser fuzz | **100,000 cases, 0 unexpected host exceptions** |
| Generated expression fuzz | **25,000 cases, 0 unexpected host exceptions** |

## Browser Host API 0.22

The `web` module exposes 107 typed functions. Of those, **101** are Browser Host operations and six are pure web helpers. `tools/validate_web_host_api.py` confirms that all 101 names are represented in the manifest, checker, canonical SH-3 kernel and Browser VM host surface. Browser-only operations fail closed in the Native reference profile.

The profile covers DOM content/query, attributes/styles/classes, form/interaction state, generic event handling, local/session/cookie storage, navigation/history, timers/animation frames, Fetch/cancellation, WebSocket, Canvas 2D, media controls, clipboard, device/environment metadata, geolocation and fullscreen. This is broad common-application coverage; it is not a claim of wrapping every external browser/vendor API.

## Real Chromium execution

Actual browser: **Chromium 144.0.7559.96**. The test launches the real Chromium binary and executes the Saga SH-3 browser VM, canonical kernel bytecode and Edition 2027 Saga source in **Blink/V8** via Chrome DevTools Protocol.

PASS checks:

- Edition 2027 source executes in the browser kernel;
- document title and DOM mutation;
- attributes, classes and inline styles;
- input, checkbox and select state;
- Canvas 2D drawing produces a real PNG data URL;
- click and input events redispatch into Saga;
- timeout event;
- Fetch using a `data:` URL with body `probe-ok`;
- browser/DOM/fetch capability detection;
- storage access on the opaque origin fails closed rather than throwing.

The host is enterprise-managed with `URLBlocklist=["*"]`. Saga **does not modify or bypass that policy**. The real-Chromium test therefore uses `about:blank` and CDP injection. Because service workers and persistent origin storage require an eligible origin, this report does not claim real-Chromium service-worker/offline-navigation qualification on this host. PWA/service-worker generation is validated separately.

Evidence: `validation/chromium-web-0.22.0.json`.

## SH-3 qualification

The monolithic validator exceeded the cumulative execution window after completing early gates, so the remaining gates were executed separately. A timed-out stage is not counted as PASS. The split run completed every qualification gate:

- strict C11 bootstrap VM and launcher: PASS;
- Stage1 → Stage2 → Stage3: PASS;
- compiler Stage2 == Stage3: PASS;
- compiler fixed-point SHA-256: `8ea80749c7aba49116742de76cca0168c8b37357fb27b3cbdd000a0739ab12d4`;
- canonical kernel compiled by Stage2 and Stage3: PASS;
- kernel Stage2 == Stage3: PASS;
- canonical kernel SHA-256: `b8ff21d64d0053b63c835fb1855f862610d51394ddff64b252b65e7f96bbc0f2`;
- Standard Core success: **23/23**;
- Standard Core diagnostics: **11/11**;
- Edition 2027: **15/15**;
- source loader / deterministic SH3IMG1 / lowered execution: PASS;
- empty-PATH `saga run`, `saga info`, and Edition-2027 `sagac`: PASS;
- source-boundary audit: PASS, 0 problems.

## Limits

The Chromium result is a real-engine language/runtime/API test, not proof that every browser capability is available under every origin or policy. WebRTC, WebUSB/Bluetooth/Serial/HID/MIDI, WebGPU/WebXR, WebCodecs/WebTransport, Push/Notifications and similar permission/device-heavy families remain outside the complete-profile claim. The internal security review is project-internal and is not a third-party certification.
