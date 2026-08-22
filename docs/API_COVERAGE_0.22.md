# Saga 0.22.0 API coverage

Saga 0.22 expands APIs by **families of operations**, not by claiming one wrapper for every external platform function.

## Broad application surfaces

| Surface | 0.22 status | Coverage model |
|---|---|---|
| Browser/Web | **broad** | 101 typed Browser Host APIs + 6 pure web helpers; generic events/attrs/styles/fetch |
| 2D/3D game | **broad baseline** | 101 typed game APIs; 2D assets/input/audio plus CPU 3D/OBJ |
| HTTP | **client + server baseline** | GET/status/POST plus listen/accept/request/respond server APIs |
| TCP | **baseline** | connect/listen/accept/send/recv/close |
| Persistent data | **transactional baseline** | key/value DB + optimistic begin/commit/rollback |
| Files/JSON/time/math/random/regex/process | **standard hosted baseline** | typed native modules retained |
| C interop | **advanced Linux x86-64 profile** | C ABI Profile 2 aggregates/callbacks/raw ownership |
| Embedded | **bare-metal baseline** | Cortex-M0/STM32 MMIO/IRQ/startup |
| WebAssembly | **scalar/freestanding baseline** | no-import embedded WASM profile |
| System introspection | **baseline** | platform/arch/cpu count/page size |

## Browser Host API count

`compatibility/web-host-api-0.22.0.json` is normative for the release inventory. `tools/validate_web_host_api.py` checks that all **101/101** names exist in the checker, canonical Saga SH-3 kernel and Browser VM host surface, while the Native reference fails closed for browser-only operations.

## What “almost all common actions” means

For browser applications, ordinary DOM manipulation, forms, event handling, browser storage, navigation/history, asynchronous scheduling, HTTP Fetch, WebSocket, Canvas 2D, media controls, clipboard, viewport/device metadata, geolocation and fullscreen can be expressed through typed Saga APIs. Generic primitives cover arbitrary event names, element attributes, inline CSS properties and HTTP methods.

It does **not** mean Saga has copied every API from every operating system, browser vendor, cloud provider or hardware SDK. Permission-heavy/device-heavy families are intentionally separated so capability boundaries remain reviewable and unsupported hosts fail closed.
