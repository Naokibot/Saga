# Saga 0.16.0 feature audit

## Language and tooling
Standard Core, lexical closures, generics, interfaces/classes, option/result, enums/records/match, deterministic package tools, self-host compiler, native standalone builds, scalar WASM, diagnostics/LSP/debugger and Native Hosted modules remain present.

## Game / graphics
- 91 typed game APIs.
- Portable RGBA8 framebuffer, PNG/JPEG, animation, camera, tilemap, particles, 2D physics, WAV and asset cache.
- Desktop windows, realtime keyboard/mouse/gamepad APIs and audio.
- Programmable OpenGL backend.
- Native2 SDL accelerated presentation backend with target-driver selection.
- Portable SIR1 shader IR: GLSL120, GLSL450, HLSL5, MSL2, WGSL.
- Vulkan loader/device probe; full Vulkan presentation remains an explicit external/implementation gap.

## Ecosystem and conformance
- Signed/trusted package registry protocol and hardened public-deployment server profile.
- Two starter packages.
- Technical second implementation evidence (Python reference vs Saga Native).
- External lab kit with lab-owned attestation fields.
- Windows/macOS/physical-controller evidence harnesses.
