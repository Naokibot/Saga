# Saga 0.23.0 application use-case matrix

`Supported` means a first-party typed/runtime path is implemented. `Expressible` means the action can be represented in Saga through `app` but needs a host adapter/capability. `Validated` records the level actually exercised in this release.

| Area | Saga source | First-party adapter | 0.23 validation |
|---|---|---|---|
| DOM/forms/events/Canvas/Fetch | Supported | Browser | real Chromium PASS |
| PWA bundle/service worker generation | Supported | Browser tooling | generation/syntax PASS; managed-policy navigation not claimed |
| HTTP client/server | Supported | Native | local E2E/regression PASS |
| DB + transactions | Supported | Native | regression/E2E baseline PASS |
| Filesystem/process/system/time | Supported | Native `app` + typed modules | unit/regression PASS |
| 2D/CPU 3D game | Supported | Native | 101 API alignment PASS |
| Notifications/share | Supported/Expressible | Browser `app` | bridge/manifest; permission UI not exercised |
| Camera/microphone | Expressible | Browser `app` | capability/bridge; physical capture not claimed |
| Bluetooth/USB/Serial/HID/MIDI/NFC | Expressible | Browser `app` | capability/bridge; hardware not claimed |
| WebGPU | Expressible | Browser `app` | adapter path; physical GPU dispatch not claimed |
| WebRTC/WebTransport | Expressible | Browser `app` | object/bridge path; live remote session not claimed |
| Payments/credentials | Expressible | Browser `app` | API bridge; real merchant/credential ceremony not claimed |
| XR/push/idle/speech | Expressible | Browser `app` | capability/bridge; device/service not claimed |
| Android/iOS proprietary actions | Expressible via namespaced `app` action | requires platform adapter | no native device qualification in this release |
| C/native vendor SDK | Supported via `unsafe` C ABI Profile 2 | Linux x86-64 qualified backend | ABI tests PASS; vendor-specific SDKs not universally tested |
| Cortex-M bare metal | Supported baseline | ARM toolchain backend | ELF/BIN/vector build validation retained |

The protocol is intentionally open-ended: a vendor operation such as `com.vendor.camera.depth_capture` can be represented without a Saga grammar change. It only becomes *executable* where a trusted adapter implements it.
