# Saga programming language — Language Specification 1.0 Draft

**Document status:** Independent language specification draft for public implementation and standards review.  
**Document identifier:** SAGA-WD-1.0-2026-08-08  
**Normative language version:** 1.0 Draft  
**Primary native implementation version:** 0.13.0  

This document is a technical working draft. It is not an ISO or IEC publication and does not imply approval, registration, certification, or endorsement by ISO, IEC, JTC 1, or SC 22.

## Foreword

Saga is designed to make introductory programming concise while retaining static type checking, exact arithmetic, explicit external capabilities, deterministic core semantics, and a path to independent implementation. The key words **shall**, **shall not**, **should**, **should not**, and **may** indicate normative requirements, recommendations, and permissions in this draft.

## 1 Scope

This document specifies:

1. the lexical and syntactic form of Saga source text;
2. the static type system and assignability rules;
3. the dynamic semantics of expressions, statements, functions, classes, exceptions, collections, and exact numbers;
4. the source-unit inclusion model;
5. the task isolation and memory model;
6. the capability boundary for hosted facilities;
7. resource-exhaustion diagnostics, diagnostic categories, conformance profiles, and command-line exit status requirements.

This document does not standardize a native ABI, object-file format, package registry protocol, graphical appearance, database engine, network protocol implementation, or operating-system installer UI.

## 2 Normative references

The following referenced specifications are indispensable for applying this document:

- ISO/IEC 10646:2020, Information technology — Universal coded character set (UCS), for the UCS/UTF encoding model;
- Unicode Standard 15.1.0;
- Unicode Standard Annex #15, Unicode Normalization Forms;
- Unicode Standard Annex #31, Unicode Identifiers and Syntax;
- RFC 3629, UTF-8;
- RFC 8259, JSON, where the hosted JSON module is implemented;
- Semantic Versioning 2.0.0, for project versions in `saga.toml`.

Where a referenced document is dated, only that edition applies.

## 3 Terms and definitions

### 3.1 implementation
A processor that accepts Saga source text and claims one or more conformance profiles.

### 3.2 conforming program
A program that satisfies all static requirements of its declared profile. Resource exhaustion by a particular host does not make the program non-conforming.

### 3.3 exact number
An `int`, `decimal`, or `rational` value whose specified mathematical value is not represented through binary floating-point approximation.

### 3.4 source unit
A UTF-8 `.saga` file included in a compilation through an entry source unit or `use "path.saga"` declaration.

### 3.5 hosted facility
A standard module whose behavior depends on an operating system, GUI framework, database, network, cryptographic provider, or optional external package.

### 3.6 capability
An explicit grant allowing a program to access a hosted resource such as a path, network endpoint, process, environment variable, database, GUI, plugin, or cloud SDK.

### 3.7 Send value
A value that can cross a task boundary by structural snapshot without sharing mutable host resources.

## 4 Conformance

### 4.1 Implementation profiles

An implementation shall declare one or more of the following profiles:

- **Portable Core Level 1 (PCL1):** lexical rules, basic declarations, exact numbers, expressions, control flow, functions, lists, basic classes, and required diagnostics for the PCL1 conformance manifest.
- **Standard Core:** all clauses 5 through 20, except hosted facilities.
- **Hosted Standard:** Standard Core plus the capability model and each hosted module claimed in its conformance statement.

A claim of Hosted Standard shall list each available module and any external dependency.

### 4.2 Conformance statement

A conforming implementation shall publish:

- implementation name and version;
- language version;
- profile or profiles;
- Unicode data version;
- implementation resource characteristics and supported host facilities;
- host resource characteristics and any deployment watchdog policy;
- hosted modules and dependencies;
- implementation-defined behavior;
- conformance-suite result and reproducible invocation.

### 4.3 No extension capture

An extension shall not silently change the meaning of a conforming Saga 0.9 program. Extension syntax shall be rejected unless explicitly enabled outside the Standard Core profile.

## 5 Source representation

### 5.1 Encoding

Source units shall be UTF-8. A single leading U+FEFF byte-order mark may appear and shall be ignored. Any other malformed UTF-8 sequence shall produce lexical category `SAGA-L001` with detailed diagnostic `SAGA-L104`, or an equivalent structured lexical diagnostic, before parsing or execution.

CRLF and CR line endings shall be normalized to LF for lexical processing and diagnostics. Line numbering starts at 1; column numbering counts Unicode scalar values and starts at 1.

### 5.2 Identifiers

Identifiers shall follow the Saga Unicode 15.1 profile:

- the first character is `_` or `XID_Start`;
- subsequent characters are `_` or `XID_Continue`;
- the complete identifier shall be NFC-normalized;
- matching is case-sensitive and shall not apply case folding;
- bidi control characters shall be rejected outside string literals;
- keywords are reserved and shall not be identifiers.

An implementation shall not silently normalize a non-NFC identifier.

### 5.3 Comments and whitespace

Whitespace separates tokens but is otherwise insignificant. `#` and `//` start a line comment outside a string literal. Semicolons are optional where the grammar permits them.

### 5.4 Literals

Integer literals are base-10 arbitrary-precision integers. Decimal literals denote exact base-10 decimal values. **Numeric literal digits are ASCII `0` through `9`**; Unicode decimal-digit characters are not numeric-literal characters. Numeric separators `_` may occur only between ASCII digits. Strings may use single or double quotes and shall decode specified escapes deterministically.

## 6 Lexical and syntactic processing

The normative grammar is `spec/saga-0.9.ebnf`. When the prose and grammar appear to conflict, the prose requirements and published defect resolutions take precedence until the next corrected draft.

An implementation shall diagnose malformed tokens before type checking. Saga defines no fixed normative ceiling for source size, token count, nesting depth, AST size, module count, exact integer size, exponent magnitude, precision, worker count, package size, or execution steps. If host resources are exhausted, the implementation shall produce a controlled resource diagnostic where recovery is possible and shall not intentionally expose a host traceback outside explicit debug mode.

No conforming implementation shall reject an otherwise-conforming program solely because it exceeds a fixed numeric limit prescribed by this specification. A host may fail to provide sufficient memory, address space, process capacity, stack capacity, storage, or execution time; implementations shall translate recoverable exhaustion into the resource diagnostic category and shall document unavoidable host termination conditions.

## 7 Source units and programs

### 7.1 Entry unit

A program has one entry source unit. For a project, `[project].entry` in `saga.toml` identifies it.

### 7.2 Source inclusion

`use "relative/path.saga"` includes a source unit relative to the containing source unit. The path shall:

- end in `.saga`;
- resolve within the project root;
- not resolve through a symbolic link in a locked package;
- not participate in a dependency cycle.

Dependencies are processed before the including unit. Each canonical source path is included once. In version 0.9, included declarations share one compilation namespace; source inclusion does not create a namespace alias.

`use identifier` imports a standard hosted module and remains an executable declaration.

### 7.3 Project manifest

A standard project manifest shall include:

```toml
[project]
name = "example"
version = "1.0.0"
language = "0.9"
entry = "main.saga"
test_dir = "tests"
```

The entry and test paths shall remain within the project root. `project.name` shall be NFC-normalized and consist of one or more Saga Unicode XID identifier components separated by ASCII hyphen (`-`). Empty components, path separators, dots, control characters, bidi formatting characters, and non-NFC spellings are rejected. Saga prescribes no fixed project-name length; host storage limits are implementation resource characteristics.

### 7.4 Lock file and package

`saga.lock` schema 1 records the language version and SHA-256, size, and relative path for the manifest and all transitively included source units. A `.sagapkg` archive shall be reproducible from unchanged locked input: member order, timestamps, permissions, and compression settings are fixed by the packaging profile. The reference canonical packaging profile stores members with ZIP method 0 (`STORED`) so archive bytes do not depend on a particular DEFLATE/zlib implementation.

## 8 Type system

### 8.1 General

Saga is statically checked. Every expression has a static type. A program with a type error shall not execute through the standard `run` command.

Standard types include:

- `unit`, `bool`, `int`, `decimal`, `rational`, `text`, `bytes`;
- `list[T]`, `map[K,V]`, `set[T]`, `option[T]`;
- function, class, interface, module, future, and native-resource types.

`any` is a dynamic boundary type. Standard-profile lint shall report public use of `any` because it reduces portability and static guarantees.

The standard host-library profile defines the following opaque resource type spellings: `db_connection`, `document_database`, `http_request`, `http_response`, `http_server`, `socket`, `websocket`, `task_pool`, `window`, `widget`, `image`, `video`, `model`, `plugin`, `spark_session`, and `gpio_pin`. These values expose no layout, pointer, or ABI; they can only be used through their defining module, are not hashable, and are not `Send`. An implementation may provide additional opaque resource types only in an implementation-defined extension profile.

### 8.2 Assignability

A value is assignable when:

- source and target types are identical;
- an `int` is assigned to `decimal` or `rational` without information loss;
- a class value is assigned to an implemented interface or ancestor class;
- generic arguments satisfy the declared invariant relationship;
- `some(v)` has target `option[T]` and `v` is assignable to `T`;
- `none()` is contextually assigned to an `option[T]`.

No implicit text conversion, truthiness conversion, decimal-to-int truncation, or nullable conversion is permitted.

### 8.3 `let` and `var`

`let` creates an immutable binding. Assignment to it is a type error. `var` creates a mutable binding. Mutation of an object through a `let` binding is governed by the declared mutability of the object's fields.

## 9 Values and equality

### 9.1 Primitive equality

Primitive exact numbers compare by mathematical value where an exact common representation exists. Text, booleans, bytes, and unit compare by value.

### 9.2 Collection equality

Lists, maps, sets, and option values compare structurally. Structural equality shall terminate for cyclic values; conforming Standard Core collections cannot directly contain themselves, while hosted or dynamic values shall still not cause an implementation stack overflow.

### 9.3 Object equality

Class instances use identity equality. An object equals itself and does not equal a separately constructed object merely because fields have equal values. This rule prevents private-state exposure and makes cyclic object graphs deterministic.

### 9.4 Hashable keys

Map keys and set elements shall be immutable, hashable Saga values. Lists, maps, sets, mutable objects, functions, futures, and native resources shall be rejected as keys or elements requiring hashing.

## 10 Exact numeric model

### 10.1 Integer

`int` is arbitrary precision up to the implementation's declared resource ceiling. Overflow shall not wrap. Exceeding a resource ceiling shall produce `SAGA-R002`.

### 10.2 Rational

Division of two integers returns a normalized `rational`, except division by zero. Numerator and denominator are arbitrary-precision integers, denominator is positive, and the greatest common divisor is one.

### 10.3 Decimal

Decimal literals and decimal operations use base-10 arithmetic. Precision shall be a positive integer selected by program or execution context; Saga specifies no fixed maximum precision. Rounding is round-half-even unless a future standard explicitly introduces another context. A host that cannot satisfy a requested precision shall report resource exhaustion rather than silently reducing precision.

A decimal overflow, invalid operation, underflow trap, or resource exhaustion shall be translated to a Saga exception or `SAGA-R002`; it shall not leak a host decimal exception.

### 10.4 Operators

`**` is right-associative. Unary minus has lower precedence than exponentiation, so `-2 ** 2` is `-(2 ** 2)`. An exponent shall be an exact integer. Negative integral exponents produce an exact rational where applicable.

Evaluation of binary operands is left-to-right. Short-circuit `and` and `or` evaluate the right operand only when required.

## 11 Text and bytes

Text values are sequences of Unicode scalar values. Indexing and `len` operate on scalar values, not grapheme clusters. Implementations shall document that user-perceived characters can contain multiple scalar values.

Bytes values are immutable sequences of octets. Conversion between text and bytes requires an explicit encoding operation; standard I/O uses UTF-8 unless an API explicitly says otherwise.

## 12 Collections

List, map, and set constructors create values whose element types are statically checked. Standard collection operations do not mutate the input unless the API explicitly represents a mutable native resource. Stable sort behavior, key ordering in display, and iteration order shall follow the library specification.

Higher-order operations shall check both the callable argument type and return contract at static and hosted boundaries.

## 13 Expressions and evaluation order

Subexpressions are evaluated from left to right except for short-circuit operators. Function arguments are evaluated left to right before the call. Index target is evaluated before index. Assignment target resolution occurs before the right-hand expression is committed, and a failed assignment shall not partially update the target.

A condition in `if` or `while` shall have type `bool`. Numeric or collection truthiness is not defined.

## 14 Statements and control flow

Blocks introduce lexical scope. `break` and `continue` are valid only in a loop. `return` is valid only in a function. A non-`unit` function shall return a value on every statically reachable completion path.

Range `a..b` is inclusive and accepts integers. Iteration proceeds by +1 when `a <= b` and -1 otherwise.

## 15 Functions, lexical closures, and generics

Functions have fixed arity. Parameters are immutable local bindings. Return and argument contracts are checked statically and again at a hosted/dynamic boundary. Recursive functions that cannot be inferred without a cycle shall declare a return type.

A function declaration may appear inside a function or block. Such a declaration creates a lexical closure over the nearest visible bindings. Captured `let` bindings are observed as immutable values. Captured `var` bindings denote shared lexical cells: mutation by the closure is visible to later calls and to code in the defining lexical environment. Closing over a binding shall not implicitly copy that binding.

Local function declarations are available throughout their containing block after block entry, permitting mutually recursive local functions. A local function whose type cannot be inferred without a cycle shall declare the relevant parameter/result types. Function type syntax is `fn[R]` for a zero-argument function returning `R`, and `fn[A, B, R]` for a function accepting `A, B` and returning `R`.

A closure containing local mutable state or object identity is `Send` only when a future profile explicitly defines transferable closure semantics. Under the current Standard Core task model such closures are not Process-Send and cannot cross CPU-process boundaries.

Generic parameters are invariant in Saga 0.9. Specialization shall not change observable Standard Core behavior.

## 16 Classes and interfaces

A class may extend at most one class and implement multiple interfaces. Interfaces contain abstract method contracts. Abstract classes cannot be directly instantiated. A method replacing an inherited or interface contract shall use `override`; `override` without a matching contract is an error.

`private` members are accessible only through the declaring class's implementation. Reflection, serialization, standard display (`print`/`text`), and metadata export shall not expose private members. Constructor field arguments are evaluated left to right.

## 17 Exceptions

`throw value` creates a Saga thrown exception. `try`, `catch`, and `finally` have deterministic control flow: `finally` executes after normal completion, caught failure, uncaught failure, return, break, or continue. A new failure in `finally` supersedes the pending transfer.

Resource-limit and hosted errors shall be represented through stable Saga diagnostics or catchable Saga runtime errors as specified by the API. Host tracebacks are non-conforming unless an explicit debug mode is enabled.

## 18 Option and absence

Saga has no language-level `null`. Absence is represented by `option[T]`, with `some(value)` and `none()`. Hosted JSON `null` and SQL `NULL` shall convert to `none()` at the boundary. A hosted API shall not inject a host `null` value into Standard Core state.

## 19 Task and memory model

### 19.1 Isolation

Each task executes in an isolated agent. Arguments cross the boundary through a structural snapshot. The task receives no reference to mutable caller state.

### 19.2 Send values

Primitive values, exact numbers, text, bytes, immutable collections of Send values, options of Send values, and structurally copyable class values may be Send. Database connections, sockets, GUI objects, thread pools, futures, module objects, plugin handles, and other native resources are not Send.

All isolated task creation APIs, including `spawn`, pool submission, and threaded mapping, shall enforce the same Send validation. CPU-process parallel APIs shall enforce the stricter Process-Send profile described in 19.5.

### 19.3 Happens-before

Task creation happens-before execution of the task body. Completion of a task happens-before successful return from `await`. No ordering is specified among independent task output events. A single standard `print` call is one indivisible output event.

### 19.4 Data-race guarantee

A conforming program using only Send values cannot create a shared-memory data race through Standard Core task APIs. Hosted extensions that share memory shall be outside the Standard Core claim and documented.

### 19.5 CPU process parallelism

A Hosted Standard implementation may provide `task.cpu_map`, `task.cpu_filter`, and `task.cpu_reduce`. Each CPU worker is a distinct operating-system process or equivalent execution agent capable of simultaneous CPU execution. Worker arguments and results cross a Process-Send value boundary. Process-Send includes value-semantic scalars, option values, immutable lists, maps, sets, ranges, date/time values, bytes, and errors whose contained values are also Process-Send. Native resources, futures, callable closures with local state, and object identities are not Process-Send. Worker processes inherit no filesystem, network, database, UI, process, plugin, environment, or cloud capability from the caller.

`task.cpu_reduce` requires an associative reducer for results that are independent of worker count and reduction tree. The implementation may schedule pairs in any order consistent with the documented tree-reduction algorithm.

## 20 Determinism and resources

For the same source, inputs, precision, and Standard Core semantics, evaluation shall be deterministic except where explicitly marked unspecified. Filesystem ordering, network timing, wall-clock time, random values, GUI events, task scheduling, and CPU-worker scheduling are hosted nondeterminism.

Saga 0.9 specifies **no fixed normative numeric resource ceilings**. Implementations may be constrained by address space, operating-system quotas, parser stack, decimal-provider limits, process limits, or administrator policy. Those constraints shall be reported as implementation/host resource characteristics rather than language limits. An implementation may expose opt-in watchdog budgets such as `--step-limit`; such a budget is deployment policy and shall not alter the meaning of a program that completes within the budget.

## 21 Hosted capability model

Hosted external access is denied by default. A conforming Hosted Standard implementation shall separately represent grants for:

- read paths;
- write paths;
- database paths;
- network host and optional port patterns;
- GUI access;
- process execution;
- environment variable names;
- plugin roots;
- cloud SDK access.

Network redirects shall be re-authorized at every destination. Process execution shall not invoke a shell by default. SQL APIs shall support parameterized values. Capability grants do not certify the safety of the external resource.

## 22 Diagnostics and process exit status

### 22.1 Diagnostic model

Diagnostics have two identifiers. The **category code** is stable across the Saga 0.x compatibility line and identifies the processing phase. The **diagnostic ID** identifies a specific learner- or tool-facing problem. Tools shall consume identifiers, ranges, and structured fields rather than parse localized prose.

Stable category codes are:

- `SAGA-L001`: lexical error;
- `SAGA-L002`: lexical host-resource exhaustion;
- `SAGA-P001`: syntax/source-unit error;
- `SAGA-P002`: syntax/source-unit host-resource exhaustion;
- `SAGA-T001`: static type error;
- `SAGA-T002`: type-analysis host-resource exhaustion;
- `SAGA-R001`: runtime language error;
- `SAGA-R002`: runtime host-resource exhaustion or opt-in watchdog exhaustion;
- `SAGA-I001`: implementation defect or unexpected host failure.

Standard Core diagnostic IDs include at least `SAGA-L101` through `SAGA-L106`, `SAGA-P101` through `SAGA-P102`, `SAGA-T101` through `SAGA-T111`, and `SAGA-R101` through `SAGA-R105` as listed in `spec/diagnostics-0.9.json`. The machine-readable diagnostic envelope is defined by `spec/diagnostic-schema-2.json`.

A diagnostic shall contain severity, category code, diagnostic ID, source name, 1-based line and Unicode-scalar column, an end position when known, and a human-readable title. A conforming interactive implementation should additionally provide an explanation and a suggested repair when one is known.

### 22.2 Localization

Diagnostic language shall not change program semantics, exit status, source ranges, category code, or diagnostic ID. English and Japanese diagnostic catalogues are supplied by the reference implementation. Additional translations may be provided without creating a language extension. The implementation shall fall back to English when a requested localization is unavailable.

The internal wording of an implementation diagnostic is not a conformance interface. A localization shall not require source code to use a particular natural language.

### 22.3 Machine-readable diagnostics

JSON diagnostic schema 2 is normative for the standard CLI. It contains the stable category `code`, detailed `id`, severity, localized title and message, raw implementation message when retained for compatibility, source range, help, explanation, implementation version, and locale.

A Hosted Standard distribution should also provide SARIF 2.1.0 output for integration with CI and code-review systems. SARIF output shall preserve the Saga diagnostic ID and source range.

### 22.4 Human-readable diagnostics

Text diagnostics should show the source line, a visual range marker, a concise title, a repair suggestion where available, a short explanation, and the command required to obtain the longer diagnostic explanation. Display alignment shall account for tabs, combining marks, and East Asian wide/full-width characters without changing normative source columns.

### 22.5 Exit status profile

The standard CLI profile uses:

- 0 success;
- 2 lexical error;
- 3 syntax/source-unit error;
- 4 type error;
- 5 runtime language error;
- 6 resource error;
- 7 conformance or verification failure;
- 66 input/project/package error;
- 70 internal implementation failure.

## 23 Standard command-line profile

A Standard Core distribution should provide:

- `saga run`, `check`, `test`, `repl`;
- `saga fmt --check` and `lint --standard`;
- `saga info --json`;
- `saga explain <diagnostic-id>`;
- `saga conformance --json`;
- `saga lock`, `verify`, and `pack`.

An implementation intended for editor integration should provide an LSP-compatible diagnostics bridge or an equivalent documented protocol. The reference implementation provides `saga lsp` over standard input/output and publishes the same stable diagnostic IDs and source ranges as the CLI.

The CLI shall not print a host traceback unless debug mode is explicitly requested. Diagnostic localization may be selected independently from source language and program behavior.

## 24 Implementation-defined and unspecified behavior

The following are implementation-defined and shall be reported:

- host resource exhaustion behavior, unavoidable process-termination conditions, and optional administrator watchdogs;
- decimal provider exponent range and trap configuration when finite;
- optional hosted modules and third-party providers;
- filesystem case sensitivity and path encoding at hosted boundaries;
- maximum HTTP, WebSocket, process-output, image, and database sizes.

The following are unspecified:

- relative scheduling order of independent tasks;
- order of external OS events;
- performance, allocation strategy, and garbage-collection timing;
- exact wording of diagnostics beyond stable code and required location fields.

Unspecified behavior is not undefined behavior: it shall remain within the permitted outcomes and shall not allow memory corruption or host exception leakage.

## 25 Internationalization and locale independence

### 25.1 Unicode edition

Saga Language Edition 1.0 freezes identifier membership to the vendored Unicode 15.1.0 XID profile so a future host Unicode upgrade cannot silently change source acceptance. The latest Unicode Standard at the time of this draft is newer; updating the normative identifier edition requires an explicit Saga language-edition change, regenerated tables in every conforming implementation, and conformance tests.

### 25.2 Locale-independent core

Core lexical grammar, decimal syntax, identifier matching, numeric formatting used for serialization, case sensitivity of identifiers, date/time interchange formats, and sorting guarantees shall not depend on the operating-system locale. A locale may affect diagnostic prose and explicitly locale-aware hosted facilities only.

### 25.3 Text security

Bidi control characters are rejected outside string literals. Implementations and formatters should make invisible or confusable source characters visible in diagnostics where this can prevent a discrepancy between compiler interpretation and human review.

### 25.4 Accessibility

Machine-readable diagnostics shall contain all information needed without relying on terminal colour. Human-readable diagnostics shall remain understandable with colour disabled and shall not encode severity solely by colour or cursor positioning.

## 26 Security considerations

Conformance is not a security certification. Implementations shall validate untrusted UTF-8, source nesting, task boundaries, collection keys, path containment, redirect targets, SQL parameters, process arguments, and cryptographic provider inputs. Private members shall not be exposed by standard reflection or serialization.

The capability model reduces ambient authority but does not replace OS sandboxing. Production deployments should additionally use operating-system accounts, containers, network policy, code signing, dependency review, and independent testing.

## Annex A (normative) Grammar

The normative EBNF is distributed as `spec/saga-1.0.ebnf` and its SHA-256 is recorded in the release checksum manifest.

## Annex B (normative) Conformance suite mapping

Each requirement designated as testable by a published conformance profile shall map to one or more positive or negative tests. Each portable-profile test records an identifier, clause, mode, input hash, expected output or stable diagnostic identifier/category, and supported profile. A conformance claim shall disclose untested or implementation-dependent requirements rather than infer coverage from localized output text.

## Annex C (informative) Portability guidance

Portable programs should avoid public `any`, implementation-specific hosted modules, dependence on task output order, filesystem case assumptions, and implicit environmental state. They should commit `saga.toml` and `saga.lock`, run standard lint, and verify a package before deployment.

## Annex D (informative) Standardization status

This draft and its implementation artifacts are intended to support review and a possible New Work Item Proposal. Formal international-standard status requires submission by an eligible proposer, a nominated project leader, committee approval, expert participation, consensus development, ballots, and publication through the responsible standards organizations.

## Annex E (informative) Standards-development references

The project uses ISO/IEC JTC 1/SC 22 as the intended standards venue. Market relevance, eligible proposal sponsorship, Project Leader nomination, expert participation, committee consensus and ballots are external process requirements and are not satisfied merely by conformance of an implementation. The security review plan also tracks the published ISO/IEC 24772-1:2024 language-independent vulnerability catalogue at a high level; this working draft does not claim certification or conformance to that separate standard.


## Annex N (normative) — Native independent distribution

An implementation claiming the **Saga Native Distribution** profile shall also satisfy `spec/SAGA_NATIVE_DISTRIBUTION_PROFILE_1.0_DRAFT.md`. In particular, the normal compiler/runtime commands shall not require another programming-language runtime or compiler toolchain to be installed on the end-user system. Bootstrap provenance is not an end-user runtime dependency and shall be disclosed separately.

The Saga language specification is independent of the source language used to construct an implementation. A conforming implementation written in Saga, Go, C, Rust, assembly, or another implementation language shall have the same Standard Core observable semantics.


## 27 Progressive depth and learning stability

Saga shall use one grammar and one Standard Core for beginner, standard and
advanced programs. Tooling may provide progressively richer templates, but a
learning level shall not create a dialect or change program semantics.

A conforming educational distribution should support a path in which top-level
values, conditions, loops and functions can be learned before classes, generic
abstraction, exceptions or concurrency. Advanced features remain normative and
need not be enabled through a language mode.

The reference Native CLI provides `saga learn`, `saga new --level` and
`saga explain <diagnostic-id>` as non-normative learning aids.

## 28 Generic class relations

A class base relation and each implemented interface relation may carry type
arguments. For a class `C[T]` whose declaration includes `implements I[T]`, an
instance of `C[int]` is assignable to `I[int]` and is not assignable to
`I[text]`. Generic class/interface arguments are invariant unless a future
language edition explicitly specifies variance.

Inherited fields and method contracts shall be specialized using the type
arguments supplied in the `extends` or `implements` relation before override and
interface-conformance checks are performed.

## 29 Compiler self-hosting profile

A distribution may claim the Saga Compiler Self-Hosting Profile when it satisfies
`spec/SAGA_SELF_HOSTING_PROFILE_1.0_DRAFT.md`. The reference 0.13 toolchain uses
a Stage0 → Stage1 → Stage2 → Stage3 build and requires Stage2 and Stage3 to be
byte-identical. A bootstrap runtime implementation language is provenance, not a
Saga language semantic dependency, and shall be disclosed separately.

## 30 Stability-oriented language edition

Saga Language Edition 1.0 is the target of the compatibility contract in
`docs/design/STABILITY_CONTRACT_1.0_DRAFT.md`. New projects created by the 0.13
Native tooling select language edition `1.0`; implementations may continue to
accept older project editions for migration and compatibility.
