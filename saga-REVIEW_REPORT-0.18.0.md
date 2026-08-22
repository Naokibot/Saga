# Saga 0.18.0 source review

## Scope

Reviewed Edition-2027 parser/AST/checker/runtime changes, numeric semantics, modules, generic constraints/associated types, resource movement, structured concurrency, metaprogramming, diagnostics/LSP, FFI/JIT, embedded WASM, SIR1 compute, bootstrap claims, compatibility and release linking.

## Defects found and fixed

1. **Edition keyword compatibility:** reserving new words globally broke pre-2027 source such as `task.await` and identifiers named `async`, `resource`, `module` or `await`. New syntax is now recognized contextually where practical and regression cases cover legacy identifier use.
2. **Compile-time optimizer robustness:** comptime folding reached a nil AST path and could panic. The optimizer now handles the relevant node lifecycle safely; compile-time folding tests pass.
3. **Moved-resource reassignment:** static analysis allowed a moved mutable resource binding to be assigned a fresh resource, but runtime moved state remained set. Assignment now resets the cell's moved flag, matching static semantics.
4. **FFI build-profile test:** the normal-build fail-closed test was incorrectly applied to explicitly enabled `sagaffi` builds. The test now checks availability against the compiled profile.
5. **LSP educational action integration:** code actions referenced a nonexistent educational-model field. Corrected to the defined lesson reason/help data.
6. **Diagnostic source escaping:** one new educational example introduced invalid Go escaping during development; corrected and covered by Go build/test.
7. **Self-host claim precision:** previous prose could imply that all runtime/compiler implementation source was Saga. The new SH profiles distinguish operational independence, Saga-driver fixed point and all-source self-hosting; only the proven levels are claimed.
8. **Default distribution linkage:** a development build made with host-default cgo was dynamically linked. The release default Native binary is rebuilt with `CGO_ENABLED=0` and `ldd` confirms `not a dynamic executable`.
9. **Validation invocation:** an intermediate 2027 conformance run used the wrong CLI selector and therefore reran Standard Core. The release evidence was regenerated with `--edition 2027` and records the intended 14/14 preview suite.
10. **Namespaced type qualification:** integrated Edition-2027 examples exposed child-local type identities leaking across module boundaries. Export cloning now qualifies class relations, fields/methods, associated bindings, function signatures/constraints, generic constructors and enum identity. Qualified enum exhaustive-match tracking was also fixed; module generic/associated/enum paths are regression-tested.

11. **Beginner diagnostic spelling:** unknown-name diagnostics previously stopped at the error. The checker now searches visible names and suggests a nearby identifier when edit distance is small, while keeping the stable diagnostic ID unchanged.

## Design review conclusions

- Advanced features are Edition/profile-gated instead of making beginner syntax more ceremonial.
- Exact numbers remain the default mathematical model; binary floats are explicit and do not silently contaminate exact arithmetic.
- Fixed-width integer types are boundary/storage types; arithmetic promotes to arbitrary `int` rather than silently overflowing.
- Resource safety is deterministic but intentionally simpler than a pervasive borrow checker: ordinary values remain easy to use, while move-only resources are tracked explicitly.
- Structured concurrency keeps Saga's isolated Send model; channels provide bounded blocking backpressure and actors serialize mutable actor-local state.
- FFI/JIT require visible `unsafe` and are optional compile-time profiles so the normal distribution remains fail-closed.
- Compile-time metaprogramming is semantic (`@derive`, restricted `comptime fn`) instead of textual substitution.
- Backend-specific GPU/native mechanisms remain outside Standard Core semantics.

## Remaining deep work, not disguised as completion

- SH-3: rewrite/independently bootstrap the complete Native runtime/compiler kernel in Saga if full all-source self-hosting is a project goal.
- General portable C ABI beyond scalar Profile 1: structs/layout, callbacks, function pointers, ownership-bearing pointers and static-library ABI.
- A whole-language optimizing JIT/AOT lowering pipeline and architecture diversity beyond the restricted x86-64 JIT profile.
- Bare-metal native targets need linker/BSP/interrupt/device-driver profiles; embedded-wasm is intentionally narrower.
- Organizationally independent implementation governance and third-party certification remain external evidence, not source-code features.
