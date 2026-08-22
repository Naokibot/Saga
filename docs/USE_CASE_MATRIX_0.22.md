# Saga 0.22.0 use-case matrix

| Use case | 0.21 | 0.22 | Evidence / boundary |
|---|---|---|---|
| CLI / algorithms | strong | strong | Standard Core + SH-3 retained |
| Web frontend | usable baseline | **broad application baseline** | 101 Browser Host APIs; actual Chromium Blink/V8 PASS |
| PWA/mobile web | baseline | **stronger** | generated manifest/service worker + expanded host API; real SW navigation not Chromium-qualified on managed host |
| Native Android/iOS | limited | limited | PWA helps deployment; no native store SDK claim |
| HTTP backend | stronger | stronger | real listen/accept/respond retained |
| Persistent app data | stronger | stronger | optimistic transactions retained |
| 2D game | good | good | 101 game APIs |
| 3D graphics | usable baseline | usable baseline | CPU perspective/depth renderer + OBJ |
| Browser realtime networking | limited | **stronger** | Fetch + WebSocket APIs |
| Browser graphics/UI | limited | **stronger** | DOM/forms/events + Canvas 2D |
| Browser media/device | limited | **stronger** | media, clipboard, viewport/device, geo/fullscreen capability-gated APIs |
| GPU/AAA 3D | insufficient | insufficient | no full PBR/animation/scene/WebGPU stack |
| Bare metal | baseline | baseline | Cortex-M0/STM32 retained |
| OS/kernel | early | early | MMIO/bare-metal exists; not a complete OS SDK |

0.22 primarily closes the browser API breadth and real-engine validation gap without broadening permissions invisibly or weakening SH-3.
