# Saga 0.25.0 validation report

Validation host: Linux x86-64. Release scope: platform qualification, external-evidence gates, mobile/runtime generation, package hardening and GA-readiness tooling.

## Internal/current-host results

| Validation | Result |
|---|---:|
| Python regression | **174/174 PASS + 4 subtests** |
| Go full suite | **PASS** |
| Go `vet` | **PASS** |
| Go Race Detector | **PASS** |
| Go FFI / JIT / FFI+JIT / Desktop / Desktop+Vulkan tagged suites | **PASS** |
| Hosted API | **168/168 PASS across 28 modules** |
| Defensive security API | **11 security + 8 crypto extensions PASS** |
| Native game API | **101/101 PASS** |
| Browser Host API | **101/101 PASS** |
| Universal App Action API | **10 source APIs / 53 browser operations PASS** |
| Real Chromium | **Chrome 144 Blink/V8 PASS** |
| Machine smoke | **file/SQLite, TCP, UDP, AES-GCM, process, WebSocket, image, video, Othello PASS** |
| Parser fuzz | **100,000 cases / 0 unexpected host exceptions PASS** |
| Expression fuzz | **25,000 cases / 0 unexpected host exceptions PASS** |
| Python ↔ independent Go Native differential corpus | **13/13 PASS** |
| Internal automated security audit | **PASS / 0 issues** |
| Native Linux host qualification | **PASS** |
| Generated Android/iOS StandardCoreRuntime build/vet/embedded execution | **PASS** |
| Python module CLI + fmt/lint/check/run/debug workflow | **PASS** |

## SH-3 self-host qualification

The monolithic validator exceeded the harness window and is not counted as PASS. Every gate was executed independently:

- strict C11 bootstrap VM and launcher: PASS;
- compiler Stage2 == Stage3: PASS, SHA-256 `8ea80749c7aba49116742de76cca0168c8b37357fb27b3cbdd000a0739ab12d4`;
- canonical kernel Stage2 == Stage3: PASS, SHA-256 `cbba9e5b42c8c41a2ecd2ecfde619368fc632299719cd7161d1b829ad32404e3`;
- Standard Core success 23/23;
- diagnostics 11/11;
- Edition 2027 Preview 15/15;
- source loader, deterministic SH3IMG1, image execution, empty-PATH run/info/sagac and source-boundary audit: PASS.

## Vulkan evidence

The production Vulkan renderer successfully creates a Vulkan instance/device, SDL surface, swapchain, acquires images, submits command buffers and reaches `vkQueuePresentKHR` for two frames on the available Chromium SwiftShader ICD. This is recorded as `PASS_SOFTWARE_DEVICE`, not physical-GPU qualification.

## External/platform evidence gates

Implemented but not qualified as physical/live PASS on this host:

- authorized live AWS account/OIDC STS roundtrip;
- physical GPIO board;
- real Spark runtime on this host;
- real pygame runtime on this host;
- Android device/emulator SDK execution;
- iOS device/simulator Xcode execution;
- native Windows execution;
- native macOS execution;
- physical gamepad;
- physical Vulkan GPU;
- independent third-party security audit;
- live non-local signed HTTPS package registry.

Dedicated CI/device-lab/attestation tools are included for each relevant gate. Cross-builds, mocks and software renderers do not inherit physical/live PASS.

## GA status

`validation/ga-readiness-0.25.0.json` is authoritative. Saga 0.25.0 is **not Core GA 1.0 yet**. Current mandatory blockers are:

1. Language Specification 1.0 Final (RC2 exists, Final deliberately does not);
2. native-host PASS on Windows and macOS;
3. live non-local signed HTTPS registry publish/search/install PASS;
4. independent signed security audit with zero open critical/high findings.

Compiler/runtime conformance, SH-3 fixed point, independent second implementation, Linux native host and developer workflow gates pass.
