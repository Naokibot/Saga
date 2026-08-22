# Saga 0.25.0 platform qualification profile

Saga 0.25.0 separates **implementation present** from **live evidence passed**.

| Profile | Implementation | Current evidence |
|---|---|---|
| Vulkan swapchain/present | Complete production path | PASS on SwiftShader software Vulkan device; physical GPU pending |
| AWS | Saga cloud adapter + live STS qualifier | Ready; authorized live account/OIDC pending |
| GPIO | input/output/PWM/read/write/on/off/close + `--allow-device` | API contract PASS; physical board pending |
| Spark | session/local/SQL/range-count + process capability | API contract PASS; real pyspark runtime pending on this host |
| pygame | finite-frame real adapter | API contract PASS; real pygame package pending on this host |
| Android | generated app/runtime + CI/device validator | generated StandardCoreRuntime build/vet/run PASS; device/APK live pending |
| iOS | generated runtime + XCFramework/device validator | generated StandardCoreRuntime build/vet/run PASS; Xcode/device live pending |
| Windows | native-host qualifier + CI | cross-build format PASS; native host evidence pending |
| macOS | native-host qualifier + CI | cross-build format PASS; native host evidence pending |
| Physical gamepad | self-hosted hardware-lab gate | pending device |
| Independent audit | signed Ed25519 attestation verifier | verifier PASS; independent audit pending |
| External registry | signed HTTPS publish/search/install qualifier | ready; authorized registry pending |

A profile status may only be upgraded by evidence from the class of environment it claims. In particular, a software GPU is not a physical GPU, a mock AWS client is not a live account, a cross-build is not native-host execution, and a project-internal security audit is not a third-party penetration test.
