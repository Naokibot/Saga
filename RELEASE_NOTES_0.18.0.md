# Saga 0.18.0 release notes

Saga 0.18.0 introduces the **Edition 2027 Preview** while keeping Language Edition 1.0 RC1 available as the stable compatibility baseline. The release is focused on the design goal "small entrance, deep ceiling": beginner programs remain concise, while advanced programs gain namespaced modules, richer types, deterministic resource ownership, structured concurrency, explicit native boundaries, compile-time evaluation and expert execution profiles.

## Language and type system

- Namespaced `module` source units, `public`/`internal` visibility, import aliases and qualified types.
- Contextual Edition-2027 syntax so legacy 1.0 programs can continue to use ordinary identifiers such as `async`, `resource`, `module`, and `await` where they are not introducing new syntax.
- IEEE-754 `float32` and `float64` with explicit exact/float conversions; Saga exact `int`/`decimal`/`rational` remain unchanged.
- Fixed-width boundary integers (`int8..int64`, `uint8..uint64`) with checked narrowing and arithmetic promotion to arbitrary-precision `int`.
- Generic `where` constraints, multiple constraints, interface constraints and associated types such as `T.Item`.
- Postfix `?` propagation for `result` and `option`.
- `resource class`, static `move` checking, `using` deterministic close and LIFO `defer`.
- `async fn`, `await`, `taskgroup`, timeout/cancellation, bounded channels/streams and serial stateful actors.
- Explicit `unsafe {}` boundary for optional foreign/native operations.
- `@derive("Equal","Hash","Debug")` hygienic compiler derivation and pure expression `comptime fn` evaluation/folding.

## Diagnostics and tooling

- Saga Diagnostics v2: stable IDs, source caret, plain-language reason, notes, guided fixes, nearby-name spelling suggestions and machine-readable `saga.diagnostic.v2` output.
- LSP advertises code actions and exposes explain/guided-fix actions for diagnostics.
- New Edition/Unicode/API-design/Evolution governance documents and SEP process.
- Edition 2027 compatibility metadata is machine readable in `compatibility/editions.json`.

## Systems and expert profiles

- Draft C ABI Profile 1 and optional `sagaffi` Linux/cgo implementation for scalar `int64`/`float64` dynamic-library calls and `extern "C"` declarations. Normal Native builds fail closed with FFI unavailable.
- Optional `sagajit` Linux x86-64/cgo scalar JIT emits and executes native x86-64 machine code for a restricted pure integer expression subset. It uses a write-then-execute (W^X) transition and is available only inside `unsafe`.
- `embedded-wasm` emits a no-import WebAssembly library for the strict portable scalar subset.
- SIR1 portable shader IR now supports `fragment` and `compute`; compute IR has deterministic CPU reference semantics and GLSL 4.50/HLSL 5/MSL 2/WGSL source generation.
- Native game API inventory grows to 92 typed functions.

## Compatibility and bootstrap

- Language Edition 1.0 remains the default stable edition; 2027 is opt-in preview.
- New edition words are contextual where practical to reduce accidental source breakage.
- The Saga-sourced compiler driver still reaches a byte-identical Stage2/Stage3 fixed point.
- Self-hosting terminology is tightened: Saga 0.18 claims an operationally independent Native distribution and a Saga-sourced fixed-point compiler driver, **not** that every runtime/compiler-kernel source file has already been rewritten in Saga.

## Review fixes made during 0.18 development

1. New `await` parsing initially broke existing `task.await`; member/name parsing now accepts contextual Edition-2027 words.
2. Other new Edition words initially risked breaking 1.0 identifiers; contextual parsing and compatibility regression tests were added.
3. Compile-time folding exposed an optimizer nil dereference; the optimizer was corrected and regression-tested.
4. Reassigning a resource variable after `move` cleared static moved state but not runtime `Cell.Moved`; runtime assignment now clears the moved flag as specified.
5. Optional FFI test logic incorrectly expected `ffi.available()==false` even in a `sagaffi` build; tests now distinguish normal fail-closed builds from enabled profiles.
6. LSP code-action integration initially referenced a nonexistent lesson field; corrected to the actual educational diagnostic model.
7. Diagnostic lesson source escaping caused a Go source error during development; corrected and covered by the full Go suite.
8. Previous self-host wording could be read as stronger than the implementation proves; SH-1/SH-2/SH-3 boundaries are now explicit.
9. The final default Linux x86-64 Native binary is rebuilt with `CGO_ENABLED=0` and verified statically linked so optional FFI/JIT/Desktop dependencies do not leak into the normal distribution.
10. Cross-module integration found unqualified interface/associated-type, generic-class, enum and exported function types inside namespaced modules; module-export cloning now qualifies relations, fields, methods, associated bindings, function signatures/constraints, generic constructors and enum identity, with regression tests.

## Deliberate non-claims

Saga 0.18 does not claim a complete arbitrary C ABI for structs/callbacks/ownership-bearing raw pointers, a general-purpose optimizing JIT, bare-metal board support, or SH-3 all-source self-hosting. These interfaces fail closed or are documented as narrower profiles rather than being presented as complete.
