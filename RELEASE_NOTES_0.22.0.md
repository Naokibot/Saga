# Saga 0.22.0 Release Notes

Saga 0.22.0 is the **Browser/API Expansion** release. It retains Standard Core 1.0 RC1, Edition 2027 Preview, SH-3, C ABI Profile 2, bare-metal support and the 0.21 application expansion while greatly widening the browser-facing API surface and adding actual Chromium execution evidence.

## Added

- **101 typed Browser Host APIs**; the `web` module now has 107 typed functions including six pure helpers.
- Generic DOM event, attribute, style and Fetch primitives for broad operation coverage without one wrapper per concrete event/property/method.
- sessionStorage/cookies, location/history, timers/animation frames, Fetch cancellation, WebSocket, Canvas 2D, media controls, clipboard, device/environment metadata, geolocation and fullscreen APIs.
- `web.capability(name)` capability probing and fail-closed behavior for unsupported/permissioned/origin-restricted hosts.
- Browser Host API machine-readable manifest and **101/101** checker/kernel/host validation.
- Actual **Chromium 144.0.7559.96** Blink/V8 execution via CDP, running canonical SH-3 browser bytecode and Edition 2027 Saga source.
- Edition directive handling in both the canonical SH-3 runtime kernel and self-host compiler path.
- Edition 2027 SH-3 qualification corpus grows from 14 to **15** cases.

## Real Chromium evidence

The Chromium run verifies title/DOM changes, attributes/classes/styles, input/checkbox/select state, real Canvas PNG output, click/input events, timers, `fetch(data:)`, and capability reporting. The host-managed `URLBlocklist=["*"]` is not modified or bypassed. Storage on the resulting opaque `about:blank` origin is expected and verified to fail closed.

## Review fixes

- Browser generic events now fall back to `on<event>` on minimal hosts that lack `addEventListener`, preserving existing test-double compatibility.
- `on_click` retains its previous event dispatch shape while generic `on_event` carries richer event metadata.
- Capability checks no longer throw `SecurityError` when an opaque origin denies access to localStorage.
- Canonical SH-3 now recognizes `edition 2027` instead of interpreting `edition` as an ordinary unknown identifier.
- SH-3 compiler bootstrap accepts the Edition directive so empty-PATH `sagac` can compile Edition 2027 source.

## Explicit limits

0.22 does not claim every browser/vendor/hardware API. WebRTC, WebUSB/Bluetooth/Serial/HID/MIDI, WebGPU/WebXR, WebCodecs/WebTransport, Push/Notifications and similar permission/device-heavy families are not declared complete. The managed Chromium host prevents top-level PWA navigation/service-worker qualification, so real-Chromium PASS applies to Blink/V8 Saga execution and tested browser APIs, not to a service-worker offline-navigation claim.
