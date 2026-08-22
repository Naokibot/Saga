# Saga Native Codegen ABI 0.32

Status: **Preview, implemented**  
Implementation release: **Saga 0.32.0**

## 1. Purpose

Native Codegen ABI 0.32 defines the first Saga ABI in which supported Saga
functions are lowered to ordinary machine-code functions in per-module native
object files. A call from one Saga module to another becomes a native symbol
reference resolved by the host linker. The Go Standard Runtime is not part of
this profile's link graph.

This profile is intentionally smaller than Standard Core. Unsupported language
semantics fail closed rather than falling back silently to a runtime interpreter.
Use `--profile standard` or `--profile object` when complete Standard Core
semantics are required.

## 2. Build profile

```text
saga build ENTRY --target native --profile codegen [--build-dir DIR] [-o FILE]
```

Each source unit becomes one host relocatable object (`.o` or `.obj`). The final
executable is linked from:

1. a small C startup object;
2. one native object per Saga source unit;
3. the Saga ABI 0.32 C support object.

No Go runtime archive is linked by this profile.

## 3. Function symbol identity

Every top-level Saga function in a successfully code-generated source graph has
a deterministic linker-visible symbol:

```text
saga_abi032_m<UTF8-HEX-MODULE-IDENTITY>_f<UTF8-HEX-FUNCTION-NAME>
```

For namespaced modules, module identity is the declared `module` name. For the
entry/legacy unit, identity is its path-independent virtual source identity
relative to the project root.

Changing a function body does not change its symbol. Renaming the module or
function does.

## 4. Stable ABI value classes

ABI 0.32 defines these direct value classes:

| Saga type | C ABI representation | Notes |
|---|---|---|
| `int` | `int64_t` | checked deployment subset; overflow terminates fail-closed |
| `bool` | `uint8_t` | `0` false, non-zero true; generated code canonicalizes to 0/1 |
| `unit` return | `void` | unit-valued parameters are not defined in 0.32 |

Saga Standard Core `int` remains arbitrary precision. Therefore this profile is
a checked int64 deployment subset, not a redefinition of Standard Core `int`.
Values outside the supported subset must not be silently truncated.

## 5. Direct call semantics

A call such as:

```saga
use "math.saga" as math
public fn answer(x: int) -> int = math.twice(x) + 2
```

lowers to an ordinary external symbol call. The caller object contains an
undefined relocation for the `math.twice` symbol and the callee module object
defines that symbol. The OS linker resolves the relocation.

Saga's left-to-right argument evaluation order is preserved by materializing
arguments into temporaries before issuing the C/native call.

## 6. Control flow and arithmetic

The implemented 0.32 direct subset includes:

- function calls, forward calls, recursion and mutual recursion within a source unit;
- public cross-module function calls;
- `let`, `var`, and Natural first-assignment locals;
- assignment to scalar locals;
- `if` / `else`;
- `while`;
- inclusive integer `for ... in a..b` in ascending or descending direction;
- `break` and `continue`;
- integer `+`, `-`, `*`, `%`, unary negation and `abs`;
- boolean logic and comparisons;
- short-circuit `and` / `or`;
- one-argument `print` for `int`, `bool`, and `unit`.

Integer add/subtract/multiply/negate use checked operations. Modulo by zero is a
stable runtime failure. Signed remainder follows Saga/Python floor-remainder
semantics rather than C's truncating remainder rule.

Exact rational `/` is not lowered by ABI 0.32.

## 7. Native ABI artifacts

For each module the build emits:

- `<module>.nabi.json` — canonical public ABI description and ABI SHA-256;
- `<module>.nabi.h` — C-compatible declarations for public Saga functions;
- native relocatable object;
- object cache manifest with source hash, dependency ABI hashes and object hash.

The public ABI hash includes exported function name, parameter classes, result
class and linker symbol. Internal function bodies do not affect an importer's ABI
hash.

## 8. Incremental compilation and link

An object cache key binds:

- Native Codegen ABI version;
- implementation version;
- target triple;
- virtual source identity;
- source SHA-256;
- the module's public native ABI SHA-256;
- direct dependency native ABI SHA-256 values;
- compiler identity.

Therefore:

- no change -> no compile, no link;
- implementation-only dependency change -> rebuild callee object, reuse importer,
  relink;
- public dependency ABI change -> rebuild dependency and importer;
- object tampering -> content hash mismatch and rebuild;
- unchanged complete link input set -> skip linker.

Build publication uses temporary files plus atomic replacement under a
cross-process build-directory lock.

## 9. Fail-closed boundary

ABI 0.32 does **not** silently lower these Standard Core features:

- arbitrary-precision values outside checked int64 deployment range;
- exact rational division;
- `text` and collection ABI values;
- classes and methods;
- closures / lexical functions;
- `option` / `result` propagation;
- exceptions;
- hosted/native modules;
- dependency-module top-level initialization;
- unit-valued function parameters.

When any of these is required, compilation fails with an AOT error before the
final executable is replaced.

## 10. Compatibility rule

The symbol prefix contains `abi032`. A future incompatible native ABI must use a
new ABI version/prefix. A 0.32 object must never be relabeled as compatible with
an incompatible future representation.

## 11. Evidence boundary

The qualification suite verifies on the available physical Linux x86-64 host:

- real relocatable module objects;
- machine-code bodies via object disassembly;
- caller `U` / callee `T` symbol pairing;
- absence of Go runtime symbols in the final executable;
- direct C-client linkage using generated `.nabi.h`;
- incremental ABI invalidation;
- clean-build byte reproducibility;
- fail-closed unsupported ABI types.

Code paths for other object formats are not equivalent to physical-host
qualification. Windows/macOS remain unqualified for ABI 0.32 until the same
suite runs there.
