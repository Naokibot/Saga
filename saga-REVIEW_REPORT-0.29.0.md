# Saga 0.29.0 Natural Core — Three-Perspective Review

## Scope

This review covers the new reference-language surface: natural bindings, closures/trailing blocks, method collection APIs, pipeline sugar, bare DSL arguments, migration tooling, and their interaction with the existing static checker/runtime.

## Review A — Language designer

### Findings

1. **Bare first assignment was initially mutable.** That made the shortest spelling less safe than `let` and violated Safe by Default.
2. **The first bare-call rule accepted a leading `-` argument.** In `n - 1`, the parser could interpret `-1` as a bare argument to `n`, creating a grammar surprise.
3. **Pipeline risked becoming a second call model.** It was therefore implemented by desugaring to the existing `Call` AST instead of adding separate runtime dispatch.
4. **Trailing closures could have become special DSL-only blocks.** They were instead made first-class lexical callable values.

### Fixes

- First bare assignment is immutable; only `var` opts into mutation.
- Ambiguous `f -1` bare-call syntax is rejected by grammar choice; `f(-1)` remains explicit.
- `|>` rewrites into ordinary calls.
- Closure semantics are shared by collection callbacks and library DSLs.

## Review B — Beginner / learning

### Findings

1. A beginner should be able to write `name = "Saga"`, `print "Hello"`, and a list pipeline without learning `main`, ownership syntax, or callback type declarations.
2. `filter { it + 1 }` must fail with a type error at compile time rather than becoming a truthiness convention.
3. Control-flow braces such as `if active { ... }` must never be confused with a trailing closure.
4. Multiple callback arguments require explicit names because an implicit `it` convention no longer communicates intent.

### Fixes and tests

- Added natural binding, chaining, implicit-`it`, explicit two-parameter closure, repeat-block, library-DSL, pipe and control-brace regression tests.
- Contextual callback typing enforces `bool` predicates.
- Trailing closure parsing is permitted on calls/members, while a simple control-flow condition variable keeps its following brace as the control block.

## Review C — Practical implementation / operations

### Findings

1. **Regression found:** the first contextual HOF implementation stopped rejecting named functions with the wrong parameter/return contract.
2. **Runtime mismatch found:** a `SagaClosure` passed to a parameter of `fn[...]` type passed static checking but runtime value validation did not recognize it as callable.
3. **Release evidence mismatch found:** the 0.28 source manifest correctly rejected the modified source tree.
4. **Cross-implementation limitation:** the independent Go/native 0.28 implementation does not yet implement the complete Natural 0.29 grammar and must not be relabeled as 0.29-conforming.

### Fixes

- Added explicit callback-contract checking for parameter acceptance, arity and result type.
- Added `SagaClosure` to runtime `fn` validation.
- Added 0.29 release/version plumbing and a new source-manifest generation step.
- Kept independent/native parity as an open release gate instead of fabricating conformance.

## Result

The reviewed Python Natural Core is internally consistent for the implemented surface after the fixes above. Remaining blockers are documented as blockers, not silently converted to PASS evidence.

---

## Follow-up review — 2026-08-12

A second implementation-focused review was performed against the packaged 0.29.0 Natural Core source rather than relying on the earlier validation report.

### Additional defects reproduced

1. **Standard native closure bundle false rejection.** The Natural feature detector treated assignment to a lexically captured `var` inside a nested function as a new first-assignment binding because it discarded the enclosing declaration scope. This caused `test_standard_native_bundle_supports_closure` to fail before Go compilation.
2. **Specified first-class closure expression was not parseable.** The Natural Core grammar documented `{ ... }` as an expression, but the parser only accepted closures as trailing call blocks. `greet = { print("Hello") }` therefore failed in the parser.
3. **Closure `return` semantics disagreed with the specification.** `return` in a closure was rejected when no named function was active, and inside an enclosing function it inherited the enclosing function's return type instead of the closure's return type.
4. **Control-flow body braces could be stolen by trailing-closure parsing.** `if ready() { ... }` could parse the body as a trailing closure on `ready()` and then fail when the parser expected the real `if` body.
5. **Callable boundaries leaked loop control context.** A closure or nested function declared inside a loop could type-check `break`/`continue`, allowing those control signals to target an enclosing caller loop.

### Corrections applied

- The AOT Natural-feature walk now carries lexical declaration scope into nested functions and closures.
- Brace-delimited closures are accepted in expression position; statement-leading braces remain ordinary blocks.
- Uncontextual omitted-parameter closures are inferred as zero-argument closures; contextual one-argument callbacks still receive `it`.
- Closure return types are tracked independently, checked across paths, and no longer inherit an enclosing function's return type.
- `if` / `while` / `for` header parsing reserves the following body brace. Parentheses explicitly re-enable trailing closures inside a control-flow header, e.g. `if (values.any { it > 0 }) { ... }`.
- Functions and closures reset loop-control context. The runtime also defensively rejects leaked `break`/`continue` signals at callable boundaries.
- Regression tests and self-conformance cases were added for each repaired behavior.

### Follow-up result

No Critical/High security finding was discovered in this review. The defects above were language-correctness and control-flow-boundary issues and have been fixed in the reviewed package. Independent Go/native Natural 0.29 parity remains an open qualification gate.

### Final regression status

After the follow-up fixes, the complete unittest suite was executed in one process to detect ordering/global-state leakage: **250 / 250 PASS** in 45.405 seconds. Built-in self-conformance is **21 / 21 PASS**, and fuzz smoke completed 100,000 parser cases plus 25,000 expression cases with zero unexpected host exceptions.

## Third review — state, migration, and desugaring boundaries

A third review intentionally avoided repeating the previous closure/control-flow checks and focused on source transformation safety, pipeline lowering, guaranteed-return analysis, and incremental REPL state.

### Additional defects reproduced

1. **Migration rewrote protected text.** `saga migrate` applied regex replacements inside string literals and `//` / `#` comments, changing user data/documentation.
2. **Pipeline lowering broke legacy middle-collection HOFs.** `reduce(function, initial)` and `find(function, fallback)` appended the piped collection instead of inserting it in the historical second position.
3. **Natural pipeline names were incomplete.** Instruction-level forms such as `|> map`, `|> distinct`, `|> sorted`, `|> take`, `|> fold`, and `|> none` resolved as unknown globals or the unrelated Option `none()` builtin.
4. **Duplicate closure parameters were accepted.** `{ value, value -> ... }` silently rebound the first parameter and used the second argument.
5. **Pipeline closures ignored the control-header brace boundary.** The pipeline parser could still consume `{ ... }` as a stage closure even when `if` / `while` / `for` had disabled trailing closures, reintroducing body-brace ambiguity.
6. **Guaranteed-return analysis missed valid control flow.** Non-unit functions returning through a nested block or `try/finally` were rejected even though every runtime path returned/threw.
7. **Failed REPL submissions split checker/runtime state.** A binding or function created before a runtime exception remained in the interpreter although the candidate type-checker state was discarded.
8. **Incremental class checking was not idempotent.** Existing class members were re-declared on every REPL submission, and inherited methods could later be mistaken for newly overriding methods.

### Corrections applied

- Migration now token-protects quoted strings and comments before applying conservative compatibility rewrites.
- Natural pipeline stages lower to the same typed extension surface as method chaining; transitional `reduce`/`find` preserve their legacy argument order.
- Natural `reduce(initial) { ... }` / `find { ... }` pipeline forms are distinguished from legacy forms where the syntax is unambiguous.
- Closure parameter names are checked for uniqueness during parsing.
- Pipeline-stage trailing closures now honor the control-header brace boundary; parentheses remain the explicit disambiguation mechanism.
- Return analysis now understands nested blocks and `try`/`catch`/`finally` dominance.
- Incremental execution snapshots and rolls back uncommitted top-level namespace, declarations, program entries, and newly registered resources on failure.
- Type checking tracks class-owned methods separately from inherited methods, so inheritance resolution can be repeated safely in a session.

### Third-review result

The new regression inventory adds ten dedicated tests. Formatter round-trip validation compiled 55 repository `.saga` files before and after formatting with zero round-trip failures. Fuzz smoke again completed 100,000 parser plus 25,000 expression cases with zero unexpected host exceptions. Final suite and source-manifest results are recorded in `saga-VALIDATION-0.29.0.md`.

### Independent implementation evidence

The independent Go implementation itself still passes `go test ./...`. Differential execution against the expanded 24-case self-conformance inventory matches **15 / 24** cases. The nine mismatches are the Natural 0.29 syntax/semantics cases that remain outside the Go frontend. This confirms the existing release boundary with executable evidence: the Python reference implementation is internally green, while independent Natural 0.29 parity is still an explicit blocker.

Final third-review regression totals are **260 / 260 unittest PASS**, **24 / 24 Python Self Conformance PASS**, and **125,000 / 125,000 fuzz cases without unexpected host exceptions**.

## Fourth review — type soundness and dynamic-boundary integrity

A fourth review focused on defects that can survive ordinary syntax/runtime tests: function subtyping, generic invariance, dynamic `any` contracts, incremental-runtime transactions, task isolation, and source-unit resource exhaustion.

### Additional defects reproduced

1. **Function return contracts were ignored by assignability.** A `fn(int) -> int` value could be stored as `fn(int) -> text`, allowing callers to trust a false result type.
2. **Function parameter variance used scalar widening in the unsafe direction.** A function accepting only `int` could be exposed as one accepting `decimal`.
3. **Generic containers were accidentally covariant through scalar widening.** Values such as `list[int]` and `option[int]` were accepted where `list[decimal]` / `option[decimal]` were required, contradicting Saga's invariant generic profile.
4. **Function type variables lost lexical visibility in local declarations.** `let copy: T = value` and nested local functions inside `fn outer[T]` parsed `T` as a nominal class rather than the active type variable.
5. **Unknown nominal types were not validated.** Signatures and dynamic-boundary declarations could name undeclared classes and still type-check.
6. **Local-function hoisting differed by block kind.** Ordinary blocks hoisted lexical functions, while `for` and `catch` bodies could reject an equivalent forward call even though the runtime hoisted it.
7. **`any` did not enforce concrete variable/field contracts at runtime.** A hosted/dynamic string could enter an `int` binding or field and later expose a Python exception rather than a Saga type diagnostic.
8. **REPL rollback was shallow.** Failed submissions could retain mutations made to Saga object fields or captured closure cells even though checker state rolled back.
9. **`task.spawn` accepted local Saga functions that the isolated task snapshot cannot resolve.** The failure appeared asynchronously instead of at the Send boundary.
10. **Very deep source-unit dependency chains leaked host `RecursionError`.** Module loading exhausted the host call stack without converting the event into a Saga resource diagnostic.
11. **`any -> fn[...]` checked only callability, not the callable signature.** A dynamic `fn(int)->int` could cross into `fn(int)->text` without a boundary failure.
12. **Generic runtime contracts were not concretized.** Inside `fn pick[T](fallback:T)->T`, an `any` value assigned to `T` was not checked against the concrete `T` inferred from the call, allowing a raw Python `TypeError` to escape from later statically-typed code.
13. **Invariant generic enforcement regressed standard native wildcard signatures.** Hosted APIs use contracts such as `list[any]` to mean a dynamically validated list boundary. Treating this internal API wildcard exactly like a user-declared invariant generic rejected valid `list[int]` arguments such as the `task.cpu_map` example.

### Corrections applied

- Function assignability now uses contravariant parameters and covariant results, including the result contract.
- Standard generic arguments are invariant. Contextual constructors such as `some`, `ok`, and `err` may still perform safe scalar conversion at the value boundary without making the container covariant.
- The checker carries active type-variable scope into local declarations and nested lexical functions.
- Declared nominal types and generic arity are validated after declaration shells are known, preserving legal forward references while rejecting unknown types.
- Local-function predeclaration is consistent in ordinary, loop, and catch blocks.
- Explicit runtime contracts are retained on typed cells and checked on initialization, mutation, and typed field assignment after an `any`/hosted boundary.
- REPL snapshots deep-copy Saga-owned mutable state (instances, collections, lexical environments, and local closures/functions) so failed submissions restore committed in-language state. External/native side effects remain intentionally outside transactional rollback.
- Local/captured Saga functions are rejected at the current task Send boundary; top-level functions remain supported.
- Source-unit host stack exhaustion is converted to a structured Saga parse/resource-limit diagnostic instead of exposing `RecursionError`.
- Dynamic function contracts compare callable arity/signature when runtime metadata is available; generic user functions may be specialized against the expected function type.
- Runtime generic calls infer concrete type-variable bindings from arguments and substitute those bindings into parameter, local-variable, and return contracts so `any -> T` remains checked.
- Nested `any` in standard/native function parameter signatures is treated as an explicit hosted-boundary wildcard only while matching that native API contract. User-declared generic assignment remains invariant.

### Fourth-review result

Sixteen dedicated regression tests cover the thirteen defect categories above. The complete validation totals and independent-implementation boundary are recorded in `saga-VALIDATION-0.29.0.md`. No claim is made that the Go implementation already contains these Natural 0.29 checker/runtime repairs.

### Validation-harness hardening

During a long single-process regression attempt, no persistent interpreter thread, file-descriptor, or live-child-process leak was reproduced after module completion. The stop point was an external attestation-verifier test whose two `subprocess.run` calls had no timeout. Those calls now use a 30-second timeout so CI fails closed instead of waiting indefinitely if the verifier or host environment stalls. This is recorded as test-infrastructure hardening rather than evidence of a Saga runtime leak.

## Fifth review — propagation, AOT semantic preservation, task errors, and path identity

A fifth review intentionally focused on surfaces not used as the primary lens in the earlier passes: documented-but-unimplemented control flow, interpreter/AOT semantic equivalence, asynchronous error identity, and source-path canonicalization.

### Additional defects reproduced

1. **Documented postfix `?` propagation was not lexable.** README and the Edition 2027 Preview grammar described `result`/`option` propagation, but the lexer had no `?` token and every example failed before parsing.
2. **Scalar AOT silently changed exact division.** `5 / 2` is exact `5/2` in Saga, while emitted C integer division produced `2`.
3. **Scalar AOT silently wrapped Standard arbitrary-precision integers.** `9223372036854775807 + 1` became a negative signed-64 value in native code.
4. **Scalar AOT's lexical-scope bookkeeping disagreed with emitted C blocks.** A name introduced only inside a branch could be treated as already declared after that branch, yielding invalid C or altered binding behavior.
5. **Native scalar `print` changed multi-argument layout.** One Saga `print(a, b, c)` could become multiple output lines instead of one space-separated line.
6. **Non-BMP Unicode text was emitted through invalid C escape forms.** Emoji and similar text could make otherwise supported native scalar programs fail to compile.
7. **Range endpoints with side effects were evaluated more than once by emitted C.** Saga evaluates start then end once; the old lowering reused the endpoint expressions in loop setup/conditions.
8. **C's unspecified operand/argument evaluation order could violate Saga's left-to-right semantics.** Cases the scalar backend cannot yet sequence safely now fail closed instead of producing target-dependent behavior.
9. **`abs(effectful_call())` evaluated its argument twice in generated C.** The ternary lowering duplicated the expression; it is now a checked helper call that evaluates the argument once.
10. **Scalar modulo-by-zero escaped Saga's runtime contract.** Direct C `%` could terminate through a host signal/undefined behavior. It now uses a checked helper; the `INT64_MIN % -1` corner is also handled without C overflow UB.
11. **Valid Saga identifiers collided with C reserved words.** Names such as `long` and `switch` compiled in the interpreter but produced invalid C. Scalar AOT now deterministically byte-mangles every user variable/function identifier.
12. **`task.await` / `task.all` erased Saga exception identity.** A task that `throw`-ed a Saga value was wrapped as a generic native failure; Saga-originated runtime errors are now rethrown unchanged and only unknown host exceptions are wrapped.
13. **Tool-front canonicalization could bypass the no-symlink source-entry policy.** CLI/project/debug/audit/AOT paths sometimes called `resolve()` before source validation. Caller-visible source paths and project entry/test components are now checked before canonicalization.

### Corrections and design boundary

- Added `QUESTION` token, `PropagateExpr`, parser/checker/runtime support, and conformance coverage for postfix `?`. `result` error types and enclosing `option`/`result` return contracts are checked statically; propagation uses normal Saga callable return semantics.
- The scalar AOT profile is now explicitly a **checked int64/bool deployment subset**, not a substitute for Standard arbitrary-precision/exact-numeric semantics. It traps overflow and modulo-by-zero, preserves supported evaluation order, and rejects exact rational division, power, postfix `?`, or effectful expression shapes it cannot lower without semantic drift.
- C emission uses UTF-8 byte string literals and deterministic symbol mangling instead of exposing Saga identifiers directly to the C namespace.
- Differential execution confirmed that the independent Go frontend already implements the new postfix `?` conformance case. The temporary fail-closed guard was therefore removed; Standard bundles allow `?` while continuing to reject Natural 0.29 features that remain unmatched.
- Task isolation preserves Saga error categories across `await`/`all` boundaries while continuing to wrap genuinely unknown host exceptions.
- Entry-path policy is enforced before path resolution and also walks project-relative components for symlinks.

### Fifth-review status

The dedicated fifth-review regression module contains **17 / 17 passing tests**. The expanded Python Self Conformance inventory is **25 / 25 PASS**, including a `result` propagation case. Full-suite, fuzz, independent-Go, manifest, and packaged-artifact results are recorded in `saga-VALIDATION-0.29.0.md` after final source binding.

## Sixth review — alias graphs, destructive paths, structured joins, and scalar-AOT semantic parity

The sixth review deliberately shifted away from the earlier parser/type-contract work. It reviewed isolation snapshots, destructive filesystem operations, lexical-path policy ordering, package output boundaries, and scalar C lowering where a native build could silently differ from the reference interpreter.

### Additional defects reproduced

1. **Task snapshots did not preserve one object graph.** The same Saga instance supplied twice, referenced by two globals, or shared between a global and an explicit task argument was copied with separate memo tables. Identity/alias relationships therefore changed inside the isolated task.
2. **`fmt` and `migrate --write` followed `.saga` symlinks discovered during directory traversal.** A project-local link could rewrite a source file outside the requested tree.
3. **Project/source symlink policy could be erased by early canonicalization.** Symlinked `saga.toml` paths and symlinked project-root aliases could be resolved before policy checks in project/package/CLI/source loading paths.
4. **Package commands could bypass the manifest symlink policy.** `_project()` resolved the caller path before `load_project`, losing evidence that the supplied manifest/project path was a symlink.
5. **Package output could overwrite a symlink target.** Both an explicit `.sagapkg` output symlink and a default `dist/` symlink could redirect an atomic replacement outside the project.
6. **Scalar AOT output could overwrite a symlink target.** `-o` was resolved before replacement, so a symlink output named an unrelated target file.
7. **Scalar AOT silently changed top-level mutable capture semantics.** A function assigning a top-level `var` created a C local with the same Saga name; reference output `2 2` became native output `2 1` without an error.
8. **Scalar AOT lacked forward function declarations.** A legal call to a later top-level function failed at the C compiler even though the reference implementation accepted it.
9. **UTF-8 C string lowering used ambiguous `\\xNN` escapes.** A following hexadecimal character (for example `"éA"`) was consumed into the escape by C, corrupting or rejecting the generated source.
10. **Native text printing was not byte-exact for embedded NUL.** `fputs` truncated otherwise valid Saga text containing U+0000.
11. **Inclusive range lowering could fail to terminate after `continue` on the endpoint.** The endpoint break check lived at the bottom of the body, so C `continue` skipped it and advanced beyond the finite Saga range.
12. **`task.all` violated the normative structured-join rule on failure.** The first failed future was rethrown immediately; later futures could still be running although the memory model says all supplied futures are complete before `task.all` returns/raises.

### Corrections applied

- Isolated task creation now uses one snapshot memo across captured globals, a bound receiver, and all explicit arguments. Alias/cycle relationships within the Send graph are preserved while the worker remains isolated from the caller.
- Source enumeration rejects symlinked `.saga` files and symlinked enumeration roots before formatting or migration writes occur.
- Source/project/package/CLI entry paths preserve lexical path evidence until no-symlink policy checks have run. Canonicalization happens after policy validation rather than before it.
- Package and AOT output paths reject symlink leaves; project-controlled relative output components (including default `dist/`) are checked before atomic replacement. The check intentionally does not reject platform-managed absolute prefixes such as macOS `/var`.
- Scalar AOT now fails closed when a function captures or mutates a top-level binding it cannot lower with reference semantics. It does not silently synthesize a local shadow.
- Scalar AOT emits prototypes for top-level functions, enabling forward calls.
- Non-ASCII/control text bytes use fixed-width octal C escapes, and native literal-text print uses `fwrite` with the exact UTF-8 byte length. This preserves non-BMP text, a following hex digit, and embedded NUL bytes.
- Inclusive range lowering performs endpoint termination/update in the C `for` update expression. Saga `continue` therefore still advances/terminates, while the endpoint itself is never incremented past INT64 bounds.
- `task.all` joins every supplied future, records the first failure in deterministic input order, and rethrows only after every future has completed. Saga error identity remains preserved.

### Sixth-review result

Seventeen dedicated regression tests cover the defects and the path-policy edge cases above. The final non-platform Python unittest inventory is **301 / 301 PASS**. Platform/evidence, self-conformance, fuzz, differential validation, and packaged-archive checks are recorded in `saga-VALIDATION-0.29.0.md` after the final source manifest is regenerated.

No claim is made that the scalar direct-C profile implements full Saga semantics: unsupported global capture and other non-preservable behavior remains explicit fail-closed territory. The Standard/reference profiles remain the complete semantic path.

### Independent implementation boundary after the sixth review

The independent Go implementation continues to pass `go test ./...`. Python↔Go differential execution remains **16 / 25**: the sixth-review runtime/path/AOT fixes introduce no new mismatch, while the nine previously identified Natural 0.29 frontend cases remain the explicit parity blocker. The reviewed release therefore remains a **Natural Core Preview**, not a claim of complete independent Natural 0.29 conformance or GA.

## Seventh review — result equality, cyclic wrappers, and scalar print semantics

The seventh review started from the distributed sixth-review ZIP rather than the working directory. It focused on semantic edges that can remain green under ordinary parser/type tests: equality wrappers, cyclic task/REPL snapshots, and observable scalar-AOT output/evaluation order.

### Additional defects reproduced

1. **`result` equality bypassed Saga object identity semantics.** `option` recursively used Saga equality, but `ResultValue` fell through to Python dataclass equality. Two distinct Saga objects with identical fields therefore compared false directly and through `some(...)`, but true through `ok(...)`.
2. **Cyclic `option`/`result` wrappers lost wrapper identity during task snapshots.** Snapshot memoization registered frozen wrappers only after recursively copying their payload. A payload graph that pointed back to its own wrapper produced a second wrapper object rather than preserving the cycle.
3. **The same cyclic-wrapper defect affected REPL rollback snapshots.** A failed incremental submission could restore a graph whose alias/cycle topology differed from the committed Saga state.
4. **Scalar AOT printed booleans as `1`/`0`.** The checked C subset represented bool as `int64_t`, and native `print` formatted every non-text scalar numerically. Reference output is `true`/`false`.
5. **Scalar AOT interleaved outer `print` output with later argument side effects.** Saga evaluates every call argument left-to-right before invoking `print`; the C emitter printed each argument immediately after evaluating it. `print(first(), second())` could therefore produce a different observable order.
6. **Scalar AOT could not print `unit` values with Saga semantics and emitted invalid C for unit-valued parameters.** A legal `print(done())` attempted to cast a void expression to an integer, and `fn take(x: unit)` emitted an illegal C `void` parameter. Unit printing is now preserved for supported direct-call/binding cases, while unit-valued parameters fail closed with an AOT diagnostic instead of delegating the failure to clang.

### Corrections applied

- `ResultValue` now participates in the same cycle-safe recursive equality path as `OptionValue`, preserving the language rule that mutable Saga objects have identity equality even when nested inside result wrappers.
- Task and REPL snapshotters allocate frozen `OptionValue`/`ResultValue` shells and memoize them **before** descending into payloads. Back-references therefore resolve to the same copied wrapper.
- Scalar AOT tracks the bool/int/unit kind of locals, parameters, direct function returns, comparisons, and logical expressions for the supported subset.
- Native scalar `print` materializes all supported arguments in Saga left-to-right order before producing outer output. Bool values use `true`/`false`; unit-valued direct calls/bindings print `unit`; integer values keep decimal formatting.
- WASM scalar printing fails closed for bool formatting until the host ABI exposes a semantics-preserving text/bool print path.
- Unit-valued function parameters are explicitly outside the current scalar C subset and are rejected before C generation.

### Seventh-review result

Six dedicated regression tests cover these defects. The complete non-platform Python unittest inventory is **307 / 307 PASS** in bounded module runs. The affected AOT/Language/Package subset was rerun after the last fail-closed unit-parameter change and passed **139 / 139**. Platform/evidence tests are rerun only after the exact-tree source manifest is regenerated.

The independent Go implementation remains outside these Python-runtime/scalar-AOT changes. Its own test suite continues to pass, and Python↔Go differential execution remains **16 / 25**, with the same nine previously known Natural 0.29 frontend mismatches. No new independent-implementation mismatch was introduced by this review.

## Eighth review — full-language readiness and independent Natural Core parity

This review changed the question from “does the current preview pass its regression suite?” to “does Saga have the architecture and implementation discipline expected of a real general-purpose programming language?” The review therefore covered language-design consistency, semantic observability, type/runtime contracts, two-implementation parity, native delivery, toolchain maturity, project/package boundaries, scalability signals, and the remaining ecosystem/governance gates.

### Defects and readiness blockers corrected

1. **Reference assignment evaluation order disagreed with the normative left-to-right rule.** Member-assignment receivers and field contracts are now resolved before evaluating the RHS, so failed targets cannot occur after RHS side effects.
2. **Natural first assignment and inferred `let` had different shadowing behavior for standard-module names.** The two immutable-binding forms now obey the same lexical rule.
3. **Relative project discovery and path-policy ordering were inconsistent.** Project walking now preserves lexical symlink evidence while still walking upward correctly from relative nested paths; source/project enumeration rejects user-controlled symlink components before canonicalization.
4. **The independent Go implementation did not implement the Natural 0.29 surface.** Natural first bindings, first-class/trailing closures, contextual closure typing, pipeline lowering, and Natural collection/text/map/set extension calls were implemented in the independent frontend/checker/runtime.
5. **Same-line bare calls remained reference-only.** Go now implements the same conservative same-line bare-argument rule as the reference parser, including trailing-block DSL calls and the subtraction ambiguity guard.
6. **The Standard Native bundle still rejected bare-call Natural source after the Go parser became capable of it.** The obsolete parity refusal was removed only after executable Go and bundle tests passed.
7. **The cross-implementation corpus was too narrow.** Self/differential conformance was expanded through Natural extension APIs, bare-call syntax/disambiguation, and a runtime diagnostic case.
8. **The Go self-conformance harness skipped execution whenever an error was expected.** This made runtime-error conformance impossible to test. It now executes after successful parse/check and validates parse, type, and runtime diagnostics end-to-end.
9. **Remainder-by-zero had an unstable detailed diagnostic across implementations.** The Python runtime now reports the standardized zero-divisor diagnostic `SAGA-R102`, matching Go while preserving the broad runtime category `SAGA-R001`.
10. **Go version metadata blurred implementation release and language target.** Existing compatibility fields remain, but `info` and conformance output now separately expose implementation version, 1.0 specification target, Natural Core Preview edition, and Natural Core 0.29 surface version.

### Independent implementation result

The Go implementation is now labeled `0.29.0` and passes its own regression suite. Python and Go both pass the expanded **44-case** Natural/Standard common conformance inventory. Direct differential execution is **44 / 44 match**. A separate deterministic generated-source differential run exercised 1,000 arithmetic, comparison, collection, closure, pipeline, and bare-call programs; after fixing the zero-remainder diagnostic mismatch, the rerun produced **0 mismatches**.

The common corpus is executable evidence, not a formal proof that the implementations are equivalent for every possible Saga program. Broader AST/property-based differential fuzzing remains a pre-GA recommendation.

### Native delivery result

A Go-based Standard Native bundle was built and executed with Natural first bindings, first-class closures, method/pipeline collection operations, same-line bare calls, and a bare-call DSL with a trailing closure. The distributed Standard path therefore no longer requires parenthesized rewrites merely because code uses Natural 0.29 syntax. The direct scalar C backend remains an intentionally smaller fail-closed profile and is not treated as the complete language implementation.

### Full-language judgement

Saga now has the implementation structure of a genuine general-purpose programming language rather than a toy interpreter: a grammar and static checker, two implementations of the declared common Natural Core profile, exact numeric semantics, objects/interfaces/generics, Option/Result/exceptions, lexical closures, task APIs, package/lock tooling, structured diagnostics, formatter/linter/LSP/REPL, capability-gated hosted APIs, and standalone native/WASM paths.

**For controlled real projects, teaching/research, internal tools, and applications willing to pin a Saga release, the language is technically usable as a serious general-purpose language preview.**

It is **not yet appropriate to call Saga 1.0 GA or a mainstream production language**. The most important remaining architectural gate is the common module model: Natural/legacy source units still share one compilation namespace, while namespaced modules with explicit exports are an Edition 2027/Go preview rather than the normative Python+Go common path. Large-project dogfooding, incremental/separate compilation evidence, broader independent differential fuzzing, public ecosystem depth, compatibility governance, third-party review/adoption, and independently controlled platform/security evidence also remain open.

See `docs/FULL_LANGUAGE_READINESS_0.29.md` for the readiness matrix and required 1.0 gates.
