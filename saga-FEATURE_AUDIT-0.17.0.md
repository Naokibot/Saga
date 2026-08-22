# Saga 0.17.0 feature audit

## Language/toolchain
Saga 1.0 RC1 Standard Core remains frozen. Native and Python implementations retain variables/types, exact arithmetic, collections, functions/closures, OOP/interfaces/generics, exceptions, option/result, enum/record/match, tasks, packages, diagnostics, LSP/debugger, deterministic build/package tooling, self-host compiler proof and scalar WASM profile.

## Graphics/game
- 91 statically typed Native game APIs; checker/runtime/manifest alignment PASS.
- Portable RGBA8 framebuffer, PNG/JPEG, animation, camera, tilemap, particles, AABB 2D physics, WAV and asset cache.
- Desktop native window, realtime keyboard/mouse/gamepad state and audio.
- OpenGL programmable renderer.
- SDL Native2 accelerated presentation with backend-driver selection.
- Optional full Vulkan framebuffer-presentation implementation through surface/swapchain/staging/queue/present; compiled on Linux, runtime device gate blocked on this host.
- SIR1 portable shader IR targets GLSL120, GLSL450, HLSL5, MSL2, WGSL plus canonical SIR1 and SHA-256 identity.
- Direct D3D11/DXGI and Metal hardware probe sources for target-host evidence.

## Implementation diversity
- Saga Native and Python reference are technically independent implementations and pass 35/35 current Standard Core cross cases.
- A third clean-room C11 subset implementation passes 11/11 declared seed cases without Go/Python dependency. It is not a full Standard Core implementation yet.
- No organizationally independent third-party implementation is claimed.

## Conformance/ecosystem
- External-lab runner and evidence schema.
- Ed25519 lab-owned evidence sealing and verification.
- Signed/trusted registry with TLS deployment profile.
- Static signed registry export and two signed starter packages.
- No independent laboratory certificate or live public Internet registry is claimed without external evidence.
