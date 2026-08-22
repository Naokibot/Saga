# Saga 0.18.0 validation report

Validation host: Linux x86-64. Release target: Saga implementation 0.18.0, stable Language Edition 1.0 RC1 plus Edition 2027 Preview.

## Final executed validation

| Validation | Result |
|---|---:|
| Python reference regression | **155/155 PASS + 4 subtests** |
| Saga Native `go test ./...` | **PASS** |
| `go vet ./...` | **PASS** |
| Go Race Detector | **PASS** |
| `sagaffi` optional profile tests | **PASS** |
| `sagajit` optional profile tests | **PASS** |
| combined `sagaffi+sagajit` tests | **PASS** |
| `sagadesktop` tests | **PASS** |
| `sagadesktop+sagavulkan` tests | **PASS** |
| Native Standard Core conformance | **17/17 PASS** |
| Edition 2027 Preview conformance | **14/14 PASS** |
| Python ↔ Native Standard Core cross suite | **35/35 PASS** |
| Native game checker/runtime/manifest | **92/92 PASS** |
| Parser fuzz | **100,000 cases; 0 unexpected host exceptions** |
| Expression fuzz | **25,000 cases; 0 unexpected host exceptions** |
| Internal automated security review | **PASS, 0 findings; project-internal, not certification** |
| Saga compiler-driver Stage2/Stage3 fixed point | **PASS, byte-identical** |
| Linux x86-64 default Native linking | **static; `ldd`: not a dynamic executable** |
| Scalar FFI live call | **PASS: libc `labs(-42) = 42`** |
| Native scalar JIT live execution | **PASS: generated machine code returned 46** |
| Embedded Portable WASM | **PASS: sections 1,3,7,10; no import section** |

## Self-host fixed-point evidence

The final static 0.18 Native release driver built the Saga compiler driver through the fixed-point sequence and Stage2/Stage3 hashes matched. This proves the declared Saga-driver fixed-point profile. It does not claim that every Native runtime/compiler-kernel source file is written in Saga.

## Binary build outputs

- Linux x86-64 default Native: built and executed on this host; statically linked.
- Linux ARM64 Portable Native: cross-built as static AArch64 ELF; target hardware execution is separate evidence.
- Windows x86-64/ARM64 Portable Native: cross-built as PE32+; this report does not relabel cross-build as target-host execution.
- macOS x86-64/ARM64 Portable Native: cross-built as Mach-O; this report does not relabel cross-build as target-host execution.
- Linux x86-64 Desktop/Vulkan/FFI/JIT expert binaries: built on this host; profile tests executed.

## Feature-specific checks

- Module namespace/public export and hidden-member rejection are covered by Edition tests; cross-module interface constraints, associated types, generic functions/classes, qualified enums and module-local return types are also regression-tested.
- Associated interface types resolve through constrained generic parameters and are checked against implementation bindings.
- `move` after-use is rejected statically (`SAGA-T180`) and runtime reassignment of a moved `var` is regression-tested.
- Actor state persists inside one serial isolated actor invocation while messages/results remain snapshot/Send bounded.
- `comptime fn` folds constant calls into literals and rejects dynamic/non-pure use.
- Diagnostics v2, nearby-name suggestions and LSP code actions have parser/checker/tool tests.
- SIR1 compute target generation and deterministic CPU reference execution are included in the Edition/game tests.

## Qualification boundaries

This report is project-generated engineering evidence, not an independent conformance-lab certificate. Optional FFI/JIT/graphics profiles deliberately have host/toolchain dependencies that do not apply to the ordinary static Saga Native distribution.
