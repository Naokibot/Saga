# Saga 0.12.0 Validation Report

Environment used for runnable validation: Linux x86-64, CPython 3.13.5, Go 1.23.2, clang 17, Swift 6.2.1, Node.js 22.16.0.

| Validation | Result |
|---|---:|
| Python unit/regression suite | **150 / 150 PASS** |
| Python self-conformance | **13 / 13 PASS** |
| Candidate clause suite | **14 / 14 PASS** |
| Go self-conformance | **11 / 11 PASS** |
| Python ↔ Go Standard Core differential | **31 / 31 PASS** |
| Hosted API entry points | **149 / 149 exercised** |
| Go `test` | PASS |
| Go `vet` | PASS |
| Go Race Detector | PASS |
| Parser fuzz | 100,000 cases, unexpected host exceptions 0 |
| Expression fuzz | 25,000 cases, unexpected host exceptions 0 |
| Internal automated security audit | PASS, 0 reported issues |
| Lexical closure mutable capture | PASS in Python and Go |
| Signed registry publish/install | PASS; Ed25519 + SHA-256 verified |
| Package capability metadata | PASS (`network` observed in test package) |
| Registry package consumed through `pkg:` import | PASS in Python and Go |
| Allowlisted NumPy bridge | PASS (`numpy.mean([1,2,3,4])` → 2.5) |
| Plugin `import os` attempt | BLOCKED |
| Standard native runtime-AOT closure program | PASS (`11`, `12`) |
| Standard WASI runtime-AOT closure program | PASS under Node WASI; output byte-for-byte matched native |
| Scalar native direct-C sample | PASS |
| Scalar WASM direct-C sample | Valid WebAssembly + execution test PASS |
| iOS StandardCoreRuntime source | `go test` host compilation PASS |
| Android StandardCoreRuntime source | `go test` host compilation PASS |
| iOS lightweight Swift Package | `swift build` PASS for scalar sample |
| Android lightweight C/JNI sources | host clang compilation PASS |

## External/hardware-qualified checks

The Hosted API harness exercises every registered Hosted API entry point. AWS, GPIO, Spark and Pygame use adapter test doubles when the live account/hardware/runtime is unavailable; this is not a substitute for those external systems.

## Mobile qualification

No Xcode/iOS device, Android SDK/NDK/emulator/device or `gomobile` executable is present in the release environment. Therefore the generated Standard Core mobile source packages were host-compiled as Go packages and the lightweight Swift/JNI paths were host-compiled, but no signed IPA, App Store build, Android AAR/APK or physical-device run is claimed.

## Registry qualification

The registry was validated over localhost using bearer publish auth, SHA-256 integrity, Ed25519 signature verification, publisher fingerprints, capability metadata, search, fetch, install and `pkg:` import. Public Internet operation needs independent infrastructure/security operations.
