# Game development with Saga Native 0.17

Saga now separates game development into portable semantics and an optional native desktop backend.

## Portable Game Profile

Available in the ordinary Saga Native build without another programming-language runtime:

- terminal canvas and drawing primitives;
- canonical RGBA8 framebuffer and alpha blending;
- pixel / rectangle / line / circle raster drawing;
- PNG and JPEG texture decoding;
- texture-region drawing and nearest-neighbour scaling;
- sprite-sheet animation;
- camera transform;
- tilemaps and atlas rendering;
- particles;
- lightweight AABB 2D physics with mass, force, impulse, restitution and gravity;
- PCM WAV decoding;
- texture/audio asset cache.

## Desktop Game Profile

Build the reference backend with the `sagadesktop` build tag and cgo. It adds:

- native resizable windows;
- real-time keyboard state;
- mouse position/buttons;
- SDL standardized game-controller enumeration/buttons/axes;
- WAV playback through the host audio device;
- OpenGL framebuffer presentation;
- fragment shaders and explicit vertex+fragment shader programs;
- renderer diagnostic information;
- second SDL accelerated presentation backend with explicit native-driver selection (for example Direct3D/Metal when exposed by the host SDL build);
- SIR1 portable shader source with deterministic GLSL/HLSL/MSL/WGSL generation;
- Vulkan loader/device probe plus an optional `sagavulkan` surface/swapchain/framebuffer-present backend; programmable Vulkan SIR1 still requires a validated SPIR-V/pipeline path.

The primary programmable reference backend uses SDL2 + OpenGL; Native2 uses SDL accelerated drivers and the optional Vulkan profile presents through Vulkan directly. This is deliberately **not** a language requirement. A second Saga implementation can use Direct3D, Metal, Vulkan or another native backend and still conform to `spec/SAGA_GAME_PROFILE_1.0_RC1.md`.

## Examples

- `examples/game/mini_dodge.saga`: dependency-free terminal game.
- `examples/game/shape_arena.saga`: portable drawing/collision sample.
- `examples/game/desktop_showcase.saga`: sprite, camera, tilemap, particles, physics, WAV, native input and programmable rendering.
- `examples/game/desktop_smoke.saga`: finite-frame desktop integration smoke test suitable for CI/Xvfb.

## API surface

The Native `game` module contains 91 statically typed functions in 0.17. The machine-readable list is `compatibility/native-game-api-0.17.0.json`.

## Validation boundary

The Linux integration test opens a real SDL window under Xvfb, creates an OpenGL context, compiles/links GLSL, uploads and presents RGBA pixels, pumps input state and queues PCM audio. In the current validation container the OpenGL renderer is Mesa llvmpipe, so this proves the OpenGL/GLSL execution path but **does not prove physical-GPU acceleration**. A virtual SDL GameController E2E test drives the production Saga gamepad path. No physical gamepad is attached to the container, so USB/Bluetooth controller hardware remains a target-device validation item.
