# Saga 0.17.0 validation report

Validation host: Debian GNU/Linux 13 x86-64. Release target: Saga implementation 0.17.0, Saga Language Edition 1.0 RC1.

## Executed and passed on this host

| Validation | Result |
|---|---:|
| Python reference regression | **155/155 PASS + 4 subtests** |
| Python Standard Core regression | **155/155 PASS** |
| Saga Native `go test ./...` | **PASS** |
| `go vet ./...` | **PASS** |
| Go Race Detector | **PASS** |
| Native Standard Core self-conformance | **17/17 PASS** |
| Python ↔ Saga Native full Standard Core cross suite | **35/35 PASS** |
| Extended cross-implementation subset | **10/10 PASS** |
| Native game checker/runtime/manifest alignment | **91/91 PASS** |
| Desktop OpenGL window/shader/audio integration under Xvfb | **PASS** |
| SDL Native2 second accelerated renderer | **PASS** (`renderer=opengl`, accelerated=true on this host) |
| SDL virtual GameController -> production Saga gamepad path | **PASS** |
| SIR1 portable shader target generation | **PASS** |
| SIR1 canonical form + SHA-256 semantic identity | **PASS** |
| Full `sagadesktop+sagavulkan` backend compilation | **PASS** |
| Strict ISO C11 clean-room implementation build | **PASS** (`-std=c11 -Wall -Wextra -Werror`) |
| Clean-room C declared conformance subset | **11/11 PASS** |
| Internal conformance-lab runner | **14/14 PASS** |
| Internal Ed25519 lab evidence seal + independent public-key verification | **PASS** |
| Signed registry localhost publish/search/trust/add | **PASS** |
| Registry native TLS health path | **PASS** |
| Signed static registry export and two-package deployment seed | **PASS** |
| Internal automated security review | **PASS; project-internal, not third-party certification** |

## Portable build outputs

- Linux x86-64: static ELF, built on this host.
- Linux ARM64: AArch64 ELF cross-built; target hardware not executed.
- Windows x86-64: PE32+ cross-built; Windows host not executed.
- Windows ARM64: PE32+ ARM64 cross-built; Windows host not executed.
- macOS x86-64: Mach-O cross-built; macOS host not executed.
- macOS ARM64: Mach-O arm64 cross-built; macOS host not executed.

Cross-building proves the portable source can be emitted for the target format; it is not target-host execution evidence.

## Vulkan qualification

0.17 adds a full framebuffer-presentation implementation containing instance/surface creation, physical-device and present-queue selection, `VK_KHR_swapchain`, swapchain images, host-visible staging buffer, RGBA/BGRA handling, command buffer recording, image-layout transitions, semaphore/fence synchronization, queue submit and `vkQueuePresentKHR`.

The Linux Vulkan-profile binary compiled and linked successfully. Runtime execution reached the Vulkan backend but reported:

```text
VULKAN_DEVICE_GATE_BLOCKED Installed Vulkan doesn't implement the VK_KHR_surface extension
```

The validation host has a Vulkan loader but no usable surface/device ICD for this operation. Therefore **Vulkan source/build is PASS, real swapchain/present execution is BLOCKED on this host**. It is not reported as a rendering PASS.

## Gamepad qualification

A virtual SDL GameController was attached and button/axis state was injected. Saga's production gamepad enumeration/open/A-button/left-axis path read those states successfully. The physical-device harness separately reported `PHYSICAL_GAMEPAD_REQUIRED`; no USB/Bluetooth controller is exposed to this container. Virtual E2E is not physical-device evidence.

## Implementation independence qualification

Saga Native and the Python reference use separate lexer/parser/checker/runtime implementations and pass the current 35-case full cross-implementation suite. A third clean-room ISO C11 source set imports/links neither implementation and passes all 11 cases in its declared subset. OOP/private/exception support remains outside that C subset. These are technical independence results; **organizationally independent third-party governance is not claimed**.

## Conformance-lab qualification

The lab kit runs the 14-case public corpus and now supports a lab-owned Ed25519 private key. Evidence embeds the public key, payload SHA-256 and signature and can be cryptographically verified. The validation run used the identity `INTERNAL-SMOKE-NOT-THIRD-PARTY`, deliberately proving the mechanism without pretending an outside laboratory performed the work. Independent certification remains an external gate.

## Package-ecosystem qualification

Local signed registry flows and TLS were executed. A static HTTPS-hostable registry tree was generated containing signed immutable `saga_hello@0.1.0` and `saga_game_math@0.1.0`, an index digest, publisher public key and fingerprint. The private signing key is not included. No external domain/hosting target was available, so **a live public Internet registry is not claimed**.

## Windows/macOS evidence status

Windows and macOS evidence harnesses, a direct Windows D3D11/DXGI hardware probe, a direct macOS Metal probe, and a GitHub Actions host matrix are included. The harnesses no longer auto-label CI/VM execution as physical hardware. The current Linux execution environment has no Windows/macOS host or VM, and no Saga repository was available in the connected GitHub account for safely running this release workflow. Therefore Windows/macOS real-host execution remains BLOCKED, not PASS.

See `validation/external-gates-0.17.0.json` for the machine-readable gate state.
