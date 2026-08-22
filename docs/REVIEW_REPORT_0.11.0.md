# Saga 0.12.0 Review Report

## Scope

Saga 0.10.1 was reviewed for the requested ecosystem/compiler/mobile expansion. The review covered Python and Go Standard Core implementations, lexical scoping, registry/package paths, plugin isolation, AOT/WASM output, generated mobile runtimes, documentation and release metadata.

## Implemented / corrected

1. **Nested lexical functions and closures** — implemented in both Python and independent Go Standard Core implementations. Local functions are block-hoisted, capture nearest lexical bindings, and mutable `var` captures use shared cells. Function types use `fn[...]`.
2. **Registry protocol** — added HTTP search/publish/fetch, fixed-version installation, `pkg:` imports and `saga.dependencies.json` pinning.
3. **Package integrity/identity** — SHA-256 download verification retained; Ed25519 publisher signing/fingerprint verification added. Static minimum capability categories are stored in registry metadata.
4. **Native/WASM build profiles** — `standard` produces standalone runtime-AOT native/WASI binaries preserving Standard Core semantics through the independent Go implementation. `scalar` directly lowers a strict int/bool/control-flow subset to C/clang and rejects unsupported semantics.
5. **Mobile generation ordering bug** — initial 0.11 development required the scalar backend before generating the Standard Core mobile runtime, so closure programs failed generation. Fixed: Standard Core mobile source is always generated; scalar C is optional.
6. **iOS/Android Standard Core runtime source** — generated Python-free Go package suitable for `gomobile bind`, plus optional direct-C lightweight runtime. This is source/runtime support, not vendor device certification.
7. **Python ecosystem bridge** — manifest-selected functions from installed Python packages can be exposed as read-only facades. Plugin source still cannot import modules. Linux strict mode bind-mounts selected site-package roots read-only inside private user/mount/PID/IPC/UTS/network namespaces.
8. **Third-party object boundary** — NumPy scalar/array results are normalized to value data; raw library object identity does not cross into Saga.
9. **Ecosystem SDK** — native Saga package, isolated Python-package bridge, WIT/Component authoring and registry deployment templates added.
10. **Capability preview** — `saga capabilities` reports statically inferred hosted authority categories with a deny-by-default policy.
11. **Documentation mismatch** — current feature/capability docs previously claimed closures/compiler/mobile/registry were planned or absent. Updated to match implementation and explicitly state external validation gaps.
12. **Android tooling metadata** — generator updated to Android Gradle Plugin 9.3.1, compile/target SDK 37 and NDK 28.2.13676358 metadata.
13. **WASM terminology** — documentation explicitly distinguishes the current WASI executable output from a WebAssembly Component binary. WIT is a companion/bridge contract.

## Important limitations not disguised as completion

- The project ships a deployable registry server/protocol, but does **not** operate a public Internet registry service.
- A large third-party *Saga-native* package population cannot be fabricated by the language implementation. 0.11 provides the author SDK, registry and Python/WASM bridges needed to grow one.
- Full Standard Core native/WASM compilation is runtime-AOT rather than an optimizing direct-lowering compiler. The direct-C backend is intentionally a smaller scalar profile.
- iOS XCFramework and Android AAR generation require `gomobile` and vendor toolchains. The release environment lacks Xcode, Android SDK/NDK and mobile devices, so App Store/Play Store/device validation is not claimed.
- Python package bridges are reduced-authority execution, not proof that arbitrary third-party code is safe.
