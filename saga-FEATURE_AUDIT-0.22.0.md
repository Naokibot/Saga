# Saga 0.22.0 Feature Audit

## Language and SH-3

Standard Core 1.0 RC1 and Edition 2027 Preview remain available. The official `saga-sh3` implementation remains qualified. The Edition 2027 SH-3 corpus is now **15/15** and includes direct source-level `edition 2027` handling in both runtime and self-host compiler paths.

## Browser/Web

The `web` module contains **107 typed functions**. **101** belong to Browser Host Profile 0.22 and cover capability discovery, DOM/query/content, attributes/styles/classes, forms/interaction, events, storage/cookies, navigation/history, timers/animation, Fetch, WebSocket, Canvas 2D, media, clipboard, device/environment, geolocation and fullscreen.

Real Chromium 144 Blink/V8 execution is PASS for DOM/form/style/Canvas/events/timer/Fetch and fail-closed capability behavior. Service-worker/offline navigation is not marked actual-Chromium-PASS because the validation host enforces a managed URL block policy.

## Game/graphics

The 0.21 **101-function** game API remains aligned, including 2D framebuffer/assets/input/audio and the CPU 3D/OBJ baseline. SIR1 fragment/compute and optional hosted graphics backends remain available.

## Server/data/systems

HTTP client/server, TCP, optimistic DB transactions, C ABI Profile 2, Cortex-M0/STM32 bare-metal, freestanding WASM and system introspection remain present.

## Explicit scope boundary

“Broad API coverage” means common application actions can be expressed with typed APIs and generalized primitives. It does not mean every browser, OS, cloud, vendor SDK, device or permission-heavy standard is copied into Saga. Unsupported capabilities fail closed and may be added through future explicit profiles.
