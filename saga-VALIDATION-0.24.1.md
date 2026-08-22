# Saga 0.24.1 validation report

Validation host: Linux x86-64. Release focus: regression correctness after source review, defensive cybersecurity, multi-process DB safety, network/process resource policy and package-registry hardening.

| Validation | Result |
|---|---:|
| Python collected tests | **161/161 PASS** (15 modules run independently) |
| Go full test suite | **PASS** |
| Go `vet` | **PASS** |
| Go Race Detector | **PASS** |
| `sagaffi` tagged suite | **PASS** |
| `sagajit` tagged suite | **PASS** |
| FFI + JIT combined tagged suite | **PASS** |
| `sagadesktop` tagged suite | **PASS** |
| `sagadesktop+sagavulkan` tagged suite | **PASS** |
| Defensive security API validator | **11 security + 8 crypto extensions PASS** |
| Hosted API entry points | **160/160 PASS across 28 modules** |
| Native game API alignment | **101/101 PASS** |
| Browser Host API alignment | **101/101 PASS** |
| Universal App Action API | **10 source APIs / 53 browser operations PASS** |
| Real Chromium | **Chrome/144.0.7559.96 PASS** |
| Parser fuzz | **100,000; 0 unexpected host exceptions PASS** |
| Expression fuzz | **25,000; 0 unexpected host exceptions PASS** |
| Machine smoke | **PASS** |
| Internal automated security audit | **PASS; 0 unresolved findings** |
| SH-3 Standard Core | **23/23 PASS** |
| SH-3 diagnostics | **11/11 PASS** |
| SH-3 Edition 2027 | **15/15 PASS** |
| SH-3 source-boundary audit | **0 problems** |

## Correctness evidence added in 0.24.1

- DB write-through-symlink regression verifies the canonical target is updated and the symlink remains a symlink.
- Python security result contracts are compiled and executed from Saga source; missing files/invalid CIDR/certificate/TLS failures return `err(...)` rather than violating the declared type.
- `result[T,E]` crosses isolated task snapshot boundaries successfully.
- Universal App duplicate JSON keys are rejected.
- Universal App file reads reject invalid UTF-8 and obey the host-action size profile.
- HTTP server rejects invalid UTF-8 request bodies and Content-Type CR/LF injection.
- Standard HTTP and process resource limits are optional administrator policies; the existing 17 MiB process-output regression still passes when no policy is set.
- Registry tests reject mismatched package identity, duplicate archive paths, excessive file count and unsafe package specs.

## SH-3 split qualification

The monolithic validator exceeded the execution window and is **not** counted as a pass. Every gate was executed separately:

- strict C11 bootstrap VM and launcher: PASS;
- Stage1→Stage2 and Stage2→Stage3 compiler rebuilds: PASS;
- compiler Stage2 == Stage3: PASS, SHA-256 `8ea80749c7aba49116742de76cca0168c8b37357fb27b3cbdd000a0739ab12d4`;
- canonical kernel Stage2 == Stage3: PASS, SHA-256 `d918e7155180f953be88cca102eced301f6007249a1461c0fe37ad51c74801c7`;
- Standard Core success 23/23, diagnostics 11/11, Edition 2027 15/15;
- source loader and deterministic SH3IMG1 PASS, token-image SHA-256 `aaa2661cdec4a115f61df6c8bc37cafc090eb388725fbb8e331755c7e286c060`;
- empty-PATH `saga run`, `saga info` (`version=0.24.1`) and `sagac` execution PASS;
- source-boundary audit PASS, 0 problems.

## Desktop / low-level profiles

Cortex-M0 and STM32F030K6 bare-metal tests PASS. FFI Profile 2 struct/callback/ownership tests PASS. Native scalar JIT executes generated machine code. SDL2 second renderer and virtual gamepad tests PASS. Native window/OpenGL/shader/audio integration PASS under Xvfb with `SDL_AUDIODRIVER=dummy`. Vulkan loader probing runs and fails closed because this host cannot create a usable Vulkan instance (`create_instance=-9`); real Vulkan rendering is therefore not claimed.

## Build outputs

Linux x86-64 portable Native was built and executed; it reports `Saga Native 0.24.1 (Standard Core)` and is statically linked. Linux ARM64, Windows x86-64/ARM64 and macOS x86-64/ARM64 portable binaries were cross-built and format-checked. Cross-build is not target-host execution.

## External limits

Hosted validation uses documented test doubles for AWS, GPIO, Spark and pygame when those targets are absent. Android/iOS device/store validation, physical GPU/gamepad qualification, Windows/macOS target execution, vendor accounts/services, independent penetration testing and third-party conformance certification remain external gates.

## Final archive re-extraction evidence

A pre-delivery 0.24.1 source ZIP was created from the fully reviewed tree, re-extracted into a clean directory, and byte-compared against the tested source tree. The source trees matched. From that re-extracted archive, `go test ./...`, `go vet ./...`, the Go Race Detector, all 161 Python tests (15 modules independently), security/Hosted/game/web/app validators, machine smoke, internal security audit, real Chromium integration and both fuzz suites completed successfully. The only subsequent changes before the delivery ZIP were release-report/manifest documentation updates; no runtime/compiler/test implementation source changed.
