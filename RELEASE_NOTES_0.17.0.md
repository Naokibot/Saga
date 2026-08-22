# Saga 0.17.0 release notes

Saga 0.17.0 hardens the graphics, external-validation and package-ecosystem work begun in 0.16. It does not change frozen Saga Language Edition 1.0 RC1 Standard Core semantics.

## Graphics and game development
- SIR1 portable shader IR now has a canonical representation and SHA-256 semantic identity in addition to deterministic GLSL 1.20/4.50, HLSL 5, MSL 2 and WGSL source generation.
- The SDL Native2 renderer remains a second accelerated presentation path and can request target SDL render drivers such as Direct3D or Metal when the target build exposes them.
- An optional `sagavulkan` backend now implements Vulkan instance/surface/device/queue selection, swapchain setup, host-visible staging, RGBA/BGRA conversion, image transitions, command submission, synchronization and `vkQueuePresentKHR` presentation.
- Direct Windows D3D11/DXGI and macOS Metal hardware probes are included in the real-host evidence kit.
- SDL virtual GameController E2E validation now exercises the production Saga count/open/button/axis path.

## Independent implementation and conformance
- Python reference ↔ Saga Native full Standard Core differential suite: 35/35 PASS.
- Extended cross-implementation subset: 10/10 PASS.
- Added a clean-room ISO C11 core implementation with no Go/Python link/import dependency. It passes all 11 seed cases in its declared subset; OOP/private/exceptions are not falsely claimed.
- External conformance lab evidence can be sealed by a lab-owned Ed25519 key and verified without the lab private key.

## Package ecosystem
- Signed registry localhost publish/search/trust/add and TLS health flow are retained and revalidated.
- Static signed-registry export provides an immutable HTTPS-hostable index and packages.
- A deployment-ready 0.17 starter registry seed includes `saga_hello` and `saga_game_math`, publisher public key/fingerprint and no private signing key.

## Correctness fixes
- Linux desktop builds no longer depend on an unversioned `libSDL2.so` development symlink when the SDL runtime SONAME is available.
- The clean-room C core no longer relies on POSIX `strtok_r`; it builds under strict ISO C11.
- Windows/macOS evidence harnesses no longer auto-label hosted CI/VM execution as physical hardware; physical-hardware status requires an explicit operator declaration.

## External gates
Windows/macOS real-host execution, a real physical gamepad/GPU, an organizationally independent implementation maintainer, independent laboratory certification, and a live public Internet registry are not self-certified. The included evidence harnesses and deployment kits are ready for those external actors/hosts. The current Linux host can build the full Vulkan backend but cannot execute its swapchain/present gate because no usable Vulkan surface/ICD is installed.
