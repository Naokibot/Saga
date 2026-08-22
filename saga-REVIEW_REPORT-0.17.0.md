# Saga 0.17.0 source review

## Scope
Reviewed graphics backends, SIR1, gamepad input, cross-implementation conformance, external lab evidence, registry deployment, real-host evidence and release portability.

## Defects found and fixed
1. **Linux desktop linker portability:** desktop build required unversioned `libSDL2.so`; changed Linux cgo link to installed SDL2 runtime SONAME.
2. **C clean-room portability:** the purported C11 implementation used POSIX `strtok_r`; replaced with standard C tokenization and strict `-std=c11 -Wall -Wextra -Werror` build validation.
3. **Physical-hardware evidence integrity:** Windows evidence hard-coded `physical_hardware=true`. Windows/macOS now require explicit operator declaration and hosted CI is not automatically physical.
4. **Shader identity gap:** SIR1 backend source existed but no canonical portable identity. Added normalized SIR1 and SHA-256 digest.
5. **Vulkan capability gap:** 0.16 only probed the loader/device boundary. Added an optional full framebuffer presentation backend through SDL Vulkan surface, swapchain, staging buffer, barriers, queue submission and present. Current host lacks a usable Vulkan ICD/surface, so runtime present is not self-certified.
6. **Gamepad hardware gap:** production APIs could not be E2E driven without physical hardware. Added SDL virtual GameController injection through the production count/open/button/axis path while retaining a separate physical-device gate.
7. **Lab evidence authenticity:** lab JSON could be produced but external ownership was not cryptographically bound. Added Ed25519 lab-owned sealing/verification. Internal smoke uses an explicit non-third-party identity.
8. **Public registry deployment boundary:** local registry functionality could be mistaken for a live ecosystem. Added immutable static export, signed starter seed and an explicit deployment-status artifact distinguishing deployable code from a live Internet service.

## Architecture decisions
- Saga-level graphics semantics remain backend-neutral; Vulkan/D3D/Metal/OpenGL/SDL are implementation mechanisms.
- Native2 can select host SDL D3D/Metal drivers; direct D3D11/Metal probes exist for independent target evidence.
- Vulkan RC1 presentation is framebuffer-transfer oriented; programmable Vulkan SIR1 requires an additional validated SPIR-V/pipeline stage before being claimed.
- Technical code independence is separated from organizational independence.
- A conformance kit is not a certificate until an external lab owns the run/review/signing process.

## Remaining external requirements
Windows/macOS target execution, physical GPU/controller evidence, external organizational ownership of a full second implementation, independent laboratory certification and live public registry hosting remain external gates, not software-generated claims.
