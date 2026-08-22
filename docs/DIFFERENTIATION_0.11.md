# Saga 0.11 differentiation

Saga does not try to beat established languages by adding more syntax. Its design concentrates normally separate concerns into one coherent model:

1. **Beginner-first syntax with strict contracts.** Programs start with Python/Ruby-like readability, while static types, explicit `option[T]`, immutable `let`, interface contracts and stable diagnostic IDs are available without changing languages later.
2. **Exact arithmetic by default.** Integer arithmetic is arbitrary precision, decimal literals use base-10 exact arithmetic, and integer division yields rational values rather than silently rounding to binary floating point.
3. **Capability transparency.** Hosted authority is deny-by-default. `saga capabilities` statically previews categories such as network, filesystem and database use before execution or package review.
4. **Safe ecosystem bridges.** Native Saga packages, allowlisted Python-package facades and WIT/WebAssembly components share a value-oriented package boundary. Python bridge code cannot use `import`; only manifest-selected functions are exposed in an isolated process/OS sandbox.
5. **Reproducible and attestable packages.** `.sagapkg` is canonical, fixed versions are recorded in `saga.dependencies.json`, SHA-256 is verified on download, and publishers may sign packages with Ed25519. Registry metadata includes inferred capability categories.
6. **Two independent Standard Core implementations.** Python and Go implementations are checked against the same observable semantics, including lexical closures.
7. **Portable compilation profiles.** The Standard profile produces standalone native or WASI bundles that preserve Standard Core semantics through the independent Go runtime; the scalar profile directly lowers a small auditable subset to C.
8. **One source, multiple mobile runtimes.** Mobile generation includes a Python-free Standard Core Go package for gomobile plus an optional tiny direct-C runtime when the source fits the scalar profile.
9. **Human-first diagnostics are not machine semantics.** Japanese/English messages are display layers over stable diagnostic IDs used by JSON, SARIF, LSP and conformance tests.

## Important trade-offs

- Saga has a much smaller community and library population than Python, JavaScript, Java, C# or Rust.
- Standard native/WASM compilation is currently runtime-AOT, not an optimizing direct-lowering compiler for the full language.
- The direct-C backend intentionally supports only a scalar subset.
- The reference registry is deployable but this project does not currently operate a public Internet registry service.
- Python ecosystem bridges reduce authority but third-party packages remain trusted dependencies.
- iOS/Android Standard Core source is generated, but device/App Store/Play Store validation requires the respective vendor toolchains and hardware.
