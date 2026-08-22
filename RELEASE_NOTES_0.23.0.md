# Saga 0.23.0 release notes — Universal App Actions

Saga 0.23.0 makes application behavior broadly expressible from Saga source through a capability-gated Universal App Action Protocol while retaining the existing typed modules.

## Main addition

`use app` provides 10 source APIs: `host`, `capability`, `capabilities`, `operation_supported`, `operations`, `invoke`, `invoke_async`, `cancel`, `on`, and `off`. Operations are namespaced text identifiers and payloads are JSON objects. This separates **source expressibility** from **host availability**: Saga source can describe a platform/vendor action without another application language, while the runtime must still have a real adapter, permission, hardware and service. Unsupported actions fail closed.

The browser profile publishes 53 first-party operations across notifications/share, media capture, files, Bluetooth/USB/Serial/HID/MIDI/NFC, contacts, wake/orientation/keyboard/pointer locks, permissions, WebGPU, WebRTC, WebTransport, payment/credentials, XR, push/idle/speech and related device actions. Native Saga provides conservative system/filesystem/time/crypto/process/HTTP operations.

## Review fixes

1. Fixed Native `use web` / `use embedded` runtime rejection despite checker acceptance.
2. Fixed Chromium UUID operation support mismatch on opaque/non-secure contexts by falling back from `crypto.randomUUID()` to `crypto.getRandomValues()` based RFC 4122 v4 generation.
3. Browser media constraint forwarding now accepts structured audio/video constraints as well as booleans.
4. All unavailable/permission-denied Universal App operations remain fail-closed; no raw JavaScript eval escape hatch was added.

## Qualification

- Go tests/vet/race: PASS.
- Python reference: 155/155 plus 4 subtests PASS.
- Game API alignment: 101/101 PASS.
- Browser Host API alignment: 101/101 PASS.
- Universal App Action API: 10 source APIs / 53 browser operations PASS.
- Real Chromium 144 Blink/V8 integration: PASS.
- Parser fuzz 100,000 and expression fuzz 25,000 with zero unexpected host exceptions: PASS.
- Internal automated security review: zero unresolved findings.
- SH-3 compiler Stage2/Stage3 and canonical kernel Stage2/Stage3: byte-identical.
- SH-3 Standard Core 23/23, diagnostics 11/11, Edition 2027 15/15, source-boundary audit 0 problems.

Real physical hardware/service validation is **not** claimed for Bluetooth/USB/Serial/HID/MIDI/NFC/camera/microphone/WebGPU/WebRTC/payment/XR/push or vendor-specific mobile APIs merely because those actions are expressible and adapters exist.
