# Saga Graphics Backend Profile — 1.0 RC1

Saga graphics APIs expose backend-neutral windows, canonical RGBA8 framebuffers, presentation, input and shader capability queries. The normative contract is observable behavior, not a vendor API.

## Backend classes
- **OpenGL programmable**: reference desktop shader backend.
- **Native2 presentation**: SDL accelerated renderer driver selected explicitly or by host policy. Target SDL builds may expose Direct3D, Metal, OpenGL, OpenGLES or software drivers.
- **Vulkan presentation**: optional `sagavulkan` build profile implementing surface/swapchain creation, staging upload, queue submission, synchronization and `vkQueuePresentKHR`. A build is not a runtime conformance PASS until those operations execute on a usable target device/ICD.
- **Direct native probes**: D3D11/DXGI and Metal device/command probes are target-host evidence tools. They do not alter Saga semantics and do not substitute for Saga renderer execution.

## Capability discovery
`game.graphics_backends()` returns presentation backends actually compiled/exposed by the implementation plus available SDL renderer-driver names. `game.vulkan_probe()` reports loader/device evidence separately so loader presence is not confused with a working swapchain.

## Portable shader boundary
SIR1 provides backend-neutral fragment-color semantics. Deterministic source generators target GLSL, HLSL, MSL and WGSL. Canonical SIR1 plus its SHA-256 digest provide portable identity. A Vulkan programmable shader claim additionally requires a validated SIR1-to-SPIR-V/pipeline path; the framebuffer-transfer Vulkan backend alone does not make that claim.

## Portability
Programs should request capabilities and provide a fallback. Direct3D, Metal, Vulkan, OpenGL, SDL and vendor driver names are implementation bindings and are not part of Standard Core language semantics.
