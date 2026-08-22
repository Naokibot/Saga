# Saga 0.35.0 Validation Report

## Measured release-candidate results

- Complete Python unittest inventory: **389 / 389 PASS** across 34 modules, executed in bounded module runs.
- Native Runtime 0.35 dedicated regression: **10 / 10 PASS**.
- Python Self Conformance: **48 / 48 PASS**.
- Go Self Conformance: **48 / 48 PASS**.
- Python ↔ Go differential conformance: **48 / 48 PASS**.
- Module graph conformance: **14 / 14 PASS**.
- Native Runtime ABI qualification: **10 / 10 PASS**.
- Native Codegen qualification: **17 / 17 PASS**.
- Python `compileall`: PASS.
- Go implementation `go test ./...`: PASS.
- Go implementation `go vet ./...`: PASS.
- Native installer `go test ./...`: PASS.
- Native installer `go vet ./...`: PASS.
- Parser fuzz: **100,000** cases.
- Expression fuzz: **25,000** cases.
- Unexpected host exceptions during fuzzing: **0**.
- Specification review lint: PASS.
- ASan/UBSan low-level Native Runtime harness: PASS with no sanitizer report.

## Feature qualification

The 0.35 native qualification runs a combined program that exercises interface dispatch, inheritance, owned text, managed Option/Result, generic specialization and exception/finally semantics in one direct-native executable. It also checks generated ABI metadata and compiles an independent C client against the exported virtual-dispatch symbol.

The GC qualification exercises young-to-old promotion, remembered-set behavior, an old-object cycle, incremental-major root/object mutation barriers, concurrent-sweep availability where C11 threads are supported, reclamation after root removal, and owned-text reachability.

## Distribution qualification

The release build produced Saga Native and `sagaruntime` binaries for:

- Linux amd64 / arm64;
- Windows amd64 / arm64;
- macOS amd64 / arm64.

Offline installers were produced for Linux amd64 / arm64 and Windows amd64 / arm64. The Linux amd64 installer was executed into a new temporary prefix; it reported Saga Native 0.35.0 and its installed conformance suite passed 48 / 48.

Cross-build success is build evidence only. Windows/macOS physical execution evidence remains a separate platform gate.

## Evidence boundary

The security audit used in this release is project-internal automated review unless explicitly accompanied by an independent signed attestation. Passing regression, sanitizer, fuzz and cross-implementation checks is strong executable evidence for the tested profiles, but is not a formal proof or a real-time/concurrent-GC certification.
