# Saga Game Profile 1.0 RC1

Status: optional profile draft for Saga Language Edition 1.0 RC1. This document is a project specification and is not an ISO/IEC standard.

## 1. Scope and conformance

This profile specifies observable game-programming semantics without standardizing a particular window system, graphics API, audio API, driver model, or vendor SDK. A conforming implementation may use SDL, Win32, Cocoa, Wayland, X11, Direct3D, Metal, Vulkan, OpenGL, software rendering, or another backend provided the Saga-level behavior required below is preserved.

The **Portable Game Profile** requires framebuffer, image texture, animation, camera, tilemap, particle, 2D physics, WAV decode, asset-management, timing, and the dependency-free terminal baseline. The **Desktop Game Profile** additionally requires native windows, non-blocking keyboard and mouse state, game controllers, audio playback, renderer presentation, and programmable shaders.

Unsupported optional profiles shall fail explicitly or report `game.desktop_available() == false`; they shall not silently emulate success.

## 2. Resources and failures

Game resources are opaque `native:*` values. APIs that can fail because of host resources or untrusted assets return `result[T,text]`. Invalid dimensions, corrupt assets, unsupported WAV encodings, unavailable devices, renderer creation failures, and shader compilation/link failures shall be reported as Saga failures without leaking a host-language traceback.

A closed window, renderer, shader, gamepad, or other closeable resource shall not be reused. Resource destruction shall be idempotent at the implementation boundary where practical. Window close-request state and actual resource destruction are distinct states.

## 3. RGBA framebuffer

`game.framebuffer(w,h)` creates a `w × h` RGBA8 pixel buffer. Width and height shall be positive and checked for address-space overflow. Pixels are row-major, the origin is the top-left, +x is right, +y is down, and each pixel contains R,G,B,A bytes in that order.

Color channels are integers 0..255. Alpha is straight alpha. Drawing uses deterministic source-over composition with defined integer rounding. Drawing outside the framebuffer is clipped and shall not corrupt memory. The Portable profile provides clear, pixel, filled rectangle, line and circle operations.

## 4. Textures and animation

`texture_load` shall decode PNG and JPEG into canonical RGBA8. File/decoder errors return `err(text)`. Texture drawing uses nearest-neighbor sampling in RC1. Region drawing shall clip at the destination and shall not read outside the source texture.

A sprite animation references a texture sheet, frame width/height, frame count and positive frames-per-second rate. For non-negative elapsed milliseconds, the frame is `floor(elapsed_ms * fps / 1000) mod frame_count`. This formula is normative for RC1.

## 5. Camera and tilemaps

A camera has world-space `x`, `y`, and positive `zoom`. For portable raster helpers, screen coordinates are obtained from `(world - camera) * zoom` with nearest integer placement as specified by the conformance vectors.

A tilemap is a rectangular integer grid with positive tile dimensions. Negative tile identifiers denote an empty tile for rendering. Atlas selection uses a declared positive column count; tile `id` maps to `(id % columns, id / columns)`.

## 6. Particles

Particles contain position, velocity, remaining lifetime, RGBA color, and positive integer size. `particles_update(dt, gravity_y)` with non-negative `dt` updates velocity by gravity, then position by updated velocity, then subtracts lifetime. Expired particles are removed. Negative `dt` shall not advance the system.

## 7. 2D physics

RC1 defines a lightweight axis-aligned rectangle physics baseline, not a general rigid-body engine. A world has gravity. Bodies have position, size, mass, velocity, force accumulator, dynamic/static state and restitution. Positive mass is required semantically; implementations may normalize an invalid non-positive supplied mass to 1 only where the current API documents that compatibility behavior.

`physics_step(dt)` integrates forces/gravity for dynamic bodies, advances positions, and resolves overlapping AABBs using deterministic finite iterations. Restitution is clamped to 0..1. Static bodies have zero inverse mass. `body_force` accumulates force; `body_impulse` changes velocity by impulse × inverse mass. RC1 does not standardize rotation, joints, continuous collision detection, friction, or broad-phase algorithms.

## 8. WAV audio

The Portable profile shall parse RIFF/WAVE PCM mono or stereo audio using 8-bit unsigned PCM or 16-bit signed little-endian PCM and expose it as canonical signed PCM16 frames. Unsupported compressed formats return `err(text)`. The Desktop profile shall provide best-effort asynchronous playback through a host audio device; device absence or initialization failure returns an error.

## 9. Asset manager

An asset manager caches successfully decoded textures and WAV clips by requested path for the manager lifetime. Concurrent accesses in one process shall not expose partially initialized resources. Cache identity is an implementation resource identity and shall not alter decoded content semantics.

## 10. Native window and input

The Desktop profile creates a resizable native window with positive dimensions. `window_poll` pumps host events and reports whether a close request has been observed; it does not itself destroy the window.

`key_down(window,name)` and mouse state APIs are non-blocking state queries after event pumping. Key names use backend-neutral human names where possible and unknown names shall return false or a documented Saga error, never memory-unsafe behavior. Mouse buttons use stable names (`left`, `middle`, `right`, plus documented extensions).

Gamepad enumeration uses the host's standardized game-controller mapping when available. Controller buttons and axes are queried by stable Saga names. Signed axes are normalized to approximately [-1,1]. Physical-device ordering is host-defined and therefore not deterministic across machines.

## 11. Renderer and shader

The Desktop profile presents the canonical RGBA8 framebuffer to a native renderer. `renderer_info` shall expose enough backend/vendor/version information for diagnostics without making that string part of program semantics.

`shader(renderer, fragment)` compiles a programmable fragment stage; `shader_program(renderer, vertex, fragment)` compiles and links explicit vertex and fragment stages. Compilation and link diagnostics are returned as Saga error text. Backend-native `shader`/`shader_program` source remains implementation-defined. Portable shaders use SIR1 as specified by `SAGA_SHADER_IR_1.0_RC1.md`; conforming SIR1 target generators shall preserve the defined RGBA transform semantics. The default presentation path shall work without a user shader.

The reference Saga Native desktop implementation provides OpenGL programmable rendering plus an SDL accelerated Native2 presentation path. Host SDL renderer drivers may bind Native2 to Direct3D or Metal. Saga Native also defines an optional `sagavulkan` build profile implementing a Vulkan surface/swapchain framebuffer-transfer presentation path; implementations shall report the path as validated only when instance, surface, physical device, swapchain, queue submission and `vkQueuePresentKHR` have executed successfully on the target host. The current Vulkan presentation path does not by itself claim backend-native programmable shader handles; SIR1-to-Vulkan programmable shading additionally requires a validated SPIR-V/pipeline stage. Direct D3D11 and Metal hardware probes are validation aids and are not Saga language semantics. **SDL2, OpenGL, Vulkan, Direct3D and Metal are implementation choices, not conformance requirements.**

## 12. Concurrency and thread affinity

Window-system and rendering backends may require OS-thread affinity. A conforming implementation shall serialize or otherwise marshal such calls so ordinary Saga task use cannot cause backend calls to execute concurrently on arbitrary OS threads in a way that violates the backend contract.

## 13. Capabilities

Portable asset loading declares filesystem capability. Desktop creation/input/rendering/audio/controller use may declare `graphics`, `gpu`, `input`, `audio`, and `gamepad` capabilities. Capability declaration is not permission by itself; deployment policy may deny access.

## 14. Determinism

Framebuffer blending, portable primitive raster behavior covered by vectors, animation frame selection, tile indexing and a fixed `physics_step(dt)` on identical portable state are intended to be reproducible within this profile. OS event ordering, physical input timing, audio scheduling, renderer performance and floating-point GPU shader results are not deterministic across hosts.

## 15. Conformance evidence

A conformance report shall identify the exact game API manifest, backend(s), OS/architecture, whether rendering was software or hardware accelerated, audio device status, gamepad hardware used, and every skipped target. Cross-compilation alone is not target-hardware validation.
