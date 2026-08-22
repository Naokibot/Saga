# Saga Universal App Action Protocol 1 — 0.23

## Goal

Saga application source must not need JavaScript, Kotlin, Swift, Java, C#, or another application language merely to describe an application action. The `app` module provides one host-neutral action protocol for synchronous operations, asynchronous operations, lifecycle/device events, cancellation, and capability discovery.

```saga
use app

if app.capability("media") {
    let request = app.invoke_async(
        "media.request_user_media",
        "{\"audio\":true,\"video\":true}",
        "camera-ready"
    )
}
```

The program above is Saga source only. A Browser Host, Native Host, mobile runtime, embedded host, or future platform adapter implements the requested operation.

## Universal primitives

- `app.host()`
- `app.capability(name)`
- `app.capabilities()`
- `app.operation_supported(operation)`
- `app.operations()`
- `app.invoke(operation, payload_json)`
- `app.invoke_async(operation, payload_json, action)`
- `app.cancel(handle)`
- `app.on(event, action)`
- `app.off(handle)`

`invoke` and `invoke_async` accept a namespaced text operation and JSON object payload. This makes the language surface open-ended without adding a keyword or new Saga compiler release for every OS or browser API.

## Meaning of “all application actions”

The protocol makes arbitrary application actions **representable in Saga source**. It does not claim that every operating system, browser, device, vendor service, entitlement, or proprietary SDK is available on every host. Availability is observable through capabilities and operations, and unsupported operations fail closed.

This distinction is normative. A host must never silently emulate a permissioned feature in a way that makes an unavailable camera, biometric sensor, payment provider, Bluetooth stack, or similar capability appear to have succeeded.

## Browser adapter categories in 0.23

The reference Browser Host includes adapters for DOM/UI through the existing `web` module plus action adapters for permissions, notifications, sharing, camera/microphone, files, Bluetooth, USB, Serial, HID, MIDI, NFC, contacts, wake locks, orientation, keyboard/pointer lock, badges, multi-screen information, WebGPU adapter acquisition, WebRTC peer setup, WebTransport, Payment Request, Credential Management, EyeDropper, WebXR session requests, Idle Detection, Push subscription, speech synthesis, vibration, network information, gamepads, and system/browser snapshots.

Many of these APIs require a secure context, a user gesture, an installed PWA, an origin, OS permission, or real hardware. The adapter therefore remains capability-gated.

## Native reference adapter categories in 0.23

The Native reference adapter implements system metadata, filesystem actions, timing, UUID generation, argv-only process execution, and bounded HTTP GET. It intentionally does not invoke a shell for `process.run`.

## Event contract

Browser asynchronous completion dispatches the normal Saga browser event bridge as:

`["app", action, operation, handle, ok, result_json]`

Lifecycle subscriptions dispatch:

`["app_event", action, event_name, handle, event_json]`

The exact host transport is not part of user source semantics.
