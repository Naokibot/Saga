# Saga Native Hosted Library — 0.23.0

The default Native Hosted build executes without another programming-language runtime. Optional Desktop/FFI/JIT and platform capability profiles are separate and fail closed when unavailable.

| Module | Baseline facilities |
|---|---|
| `io` | UTF-8 text files, existence, removal, directory listing |
| `json` | strict encode/decode and exact-number-aware values |
| `time` | Unix milliseconds, millisecond sleep |
| `math` | constants/transcendental hosted helpers |
| `random` | OS random values |
| `crypto` | SHA-256 baseline |
| `net` | TCP facilities |
| `http` | HTTP client plus bounded server/request/response profile |
| `db` | persistent key/value data plus optimistic transactions |
| `process` | argv execution without implicit shell |
| `regex` | matching helpers |
| `task` | isolated futures, timeouts/cancellation, bounded channels/streams, actors |
| `game` | 101 typed terminal/portable/optional desktop/3D functions |
| `machine` | 69 hosted control/device functions; Linux I²C/SPI/UART/CAN/PWM/IIO hardware adapters are device-capability gated |
| `web` | 107 typed browser/PWA functions; 101 Browser Host operations |
| `app` | Universal App Action Protocol: capability discovery, sync/async invocation and host events |
| `sys` | host/runtime information |
| `compiler` | compiler-driver/build support |
| `embedded` | bare-metal/WASM hosted boundary where the selected target supports it |
| `ffi` | optional C ABI Profile 2; fails closed in normal build |
| `jit` | optional native scalar JIT; fails closed in normal build |

## Universal app boundary

`app` is the extensibility layer for application actions whose concrete API differs by host. Saga source names an operation and passes a JSON object; the host adapter either performs the operation or returns a typed failure. The protocol never treats an advertised operation as proof that the user granted permission or that required hardware/service is present.

The browser profile currently publishes 53 first-party operation names covering notifications/share, media capture, files, Bluetooth/USB/Serial/HID/MIDI/NFC, contacts, wake/orientation/keyboard/pointer locks, permissions, WebGPU, WebRTC, WebTransport, payment/credentials, XR, idle, push and speech. Native first-party operations cover system/filesystem/time/crypto/process/HTTP basics. Additional proprietary operations can use namespaced operation identifiers without changing Saga syntax.

## Profile split

**Portable Game:** canonical RGBA8 framebuffer, PNG/JPEG, sprite animation, camera, tilemaps, particles, lightweight AABB 2D physics, WAV PCM decode, asset cache and CPU 3D mesh/rasterization baseline.

**Desktop Game:** native window, realtime keyboard/mouse/gamepad state, audio, renderer presentation and programmable shaders. SDL2/OpenGL/Vulkan are Native backend choices rather than normative Saga semantics.

**Expert FFI/JIT:** both require visible `unsafe` use. C ABI Profile 2 includes by-value aggregates, callbacks and ownership-aware raw pointers on validated Linux x86-64 builds. Unsupported native capabilities are rejected rather than widened implicitly.

Implementation resource limits are reported through `saga info`; they are not hidden language-level numeric ceilings.
