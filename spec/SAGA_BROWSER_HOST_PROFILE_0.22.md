# Saga Browser Host Profile 0.22

**Status:** implemented application profile for Saga 0.22.0. This profile is not a claim that every WHATWG, W3C, Chromium, WebExtension or vendor-specific API is wrapped by a dedicated Saga function.

## Goal

Provide a broad, typed browser surface that covers the common operations needed by ordinary interactive web applications while keeping host authority explicit and fail-closed. The profile uses a combination of dedicated high-level operations and generic primitives so new event names, attributes, CSS properties and HTTP methods do not require a new language release.

## Surface

The Browser Host profile contains **101 typed host operations**. Six pure `web` helpers (`escape`, `url_encode`, `element`, `document`, `route`, `query`) remain outside the host count, for **107 typed `web` functions total**.

Categories are machine-readable in `compatibility/web-host-api-0.22.0.json`:

- capability discovery and browser presence;
- element existence/query counting and document title;
- DOM text/HTML/value create/clear/remove/append/prepend;
- attributes, inline styles and class-list operations;
- focus/blur/click/scroll, checkbox/disabled/select state and bounding rectangles;
- click and generic event registration/dispatch;
- localStorage, sessionStorage and cookie operations;
- location, hash, navigation and History API operations;
- timeout, interval and animation-frame scheduling;
- online state, Fetch and cancellation;
- WebSocket open/send/close/state;
- Canvas 2D sizing, clearing, rectangles, lines, circles, text and data URLs;
- media play/pause/time/volume;
- clipboard read/write;
- viewport, device-pixel ratio, language, user agent and visibility;
- geolocation;
- fullscreen enter/exit/state.

## Generalized operations

`web.on_event(id,event,action)` accepts event names instead of requiring a dedicated wrapper per event. `set_attr`/`set_style` accept attribute/property names. `web.fetch` accepts an HTTP method, URL, body, content type and dispatch action. This is how Saga covers a large family of browser operations without pretending an infinite API list can be complete.

## Capability and permission model

`web.capability(name)` reports whether a host facility is usable. Browser-only operations fail closed in Native profiles. Permissioned or origin-restricted features such as clipboard, geolocation, storage and fullscreen shall return an explicit failure/capability result rather than silently escalating authority.

## Chromium qualification

Saga 0.22.0 is validated on **Chromium 144.0.7559.96** by executing the actual SH-3 browser VM, canonical kernel and Saga Edition 2027 source in Blink/V8 via Chrome DevTools Protocol. The executed corpus verifies DOM mutation, form state, attributes/classes/styles, real Canvas PNG output, click/input dispatch, timers, Fetch and capability reporting.

The validation host is managed with `URLBlocklist=["*"]`. That policy is **not modified or bypassed**. Therefore the real-Chromium evidence uses `about:blank`; origin-requiring localStorage is verified to fail closed there. Service-worker installation/offline top-level navigation is not claimed as Chromium-qualified on this host.

## Explicit limits

Dedicated wrappers are not provided for the complete WebRTC, WebUSB, WebBluetooth, WebSerial, WebHID, WebMIDI, WebGPU, WebXR, File System Access, WebCodecs, WebTransport, Payments, Credential Management, Notifications/Push or extension ecosystems in this profile. Those are future capability profiles and must remain explicit because many require permissions, secure contexts, devices, or vendor-specific behavior.
