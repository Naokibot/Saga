# Saga Natural Core 0.29 — Reference Semantics

Status: **Preview**. This document specifies the Natural Core surface implemented by the Saga 0.29 Python reference frontend/runtime and the independent Go/native frontend/runtime. The release conformance corpus is executed against both implementations; this measured corpus parity is not a formal proof of equivalence for every Saga program.

## 1. Binding rule

A simple assignment whose identifier is not already bound in the current lexical scope introduces an immutable binding:

```saga
name = "Saga"
```

It is semantically equivalent to an inferred immutable declaration, not to `var`. A later assignment to that binding is a type-checking error. Mutable state remains explicit:

```saga
var count = 0
count = count + 1
```

An assignment to a non-variable target does not introduce a binding.

## 2. Closure expressions

A brace-delimited expression may form a lexical closure when parsed in expression/call context:

```text
closure        := "{" [ closure_params "->" ] closure_body "}"
closure_params := IDENT ("," IDENT)*
```

For a contextually expected single-parameter function, omitted parameters expose that parameter as `it`. For zero parameters, no implicit `it` is introduced. For two or more expected parameters, explicit parameter names are required.

Without a contextual callable type, an omitted-parameter closure is inferred as a zero-argument closure. Parameterized first-class closures should therefore be given a contextual function type when parameter types cannot otherwise be inferred:

```saga
let double: fn[int, int] = { value -> value * 2 }
```

The final expression statement in the closure body is the closure result. `return` returns from the closure itself. Captures are lexical.

## 3. Trailing closure calls

A closure following an already-formed call or member invocation is appended as the final argument:

```saga
values.map { it * 2 }
repeat(3) { print("Hi") }
```

A simple variable followed by `{` is not universally interpreted as a trailing closure. This preserves unambiguous control-flow forms such as `if active { ... }` and `for value in values { ... }`.

The body brace of `if`, `while`, and `for` takes precedence over trailing-closure shorthand. When a control-flow header itself needs a trailing closure, parentheses provide the explicit disambiguation boundary:

```saga
if (values.any { it > 0 }) {
    print("positive")
}
```

## 4. Bare arguments

For DSL-oriented calls, a callable variable or member may take same-line bare arguments. The first bare argument must begin on the same source line as the callee. Parenthesized calls remain canonical when ambiguity exists.

```saga
print "Hello"
panel "Todo" { renderTasks() }
```

A leading unary `-`, `!`, or `not` is not accepted as the first bare argument. Therefore subtraction keeps its ordinary meaning and negative arguments use parentheses:

```saga
f(-1)
```

## 5. Pipeline

```text
pipeline := logical_or ("|>" pipeline_stage)*
```

The pipeline is syntax sugar and lowers to the existing `Call` / typed extension-call AST. It has no independent runtime dispatch model. Natural collection stage names are method-equivalent, so these forms have the same semantics:

```saga
values.map { it * 2 }.distinct().sorted()
values |> map { it * 2 } |> distinct |> sorted
```

For transitional higher-order builtins whose historical argument order is callback-first, lowering preserves the builtin's semantic argument order. In particular, legacy `reduce(function, list, initial)` and `find(function, list, fallback)` place the piped collection in the second argument position. Natural `fold(initial) { ... }` and Option-returning `find { ... }` lower to collection extension calls.

## 6. Natural collection surface

Sequence values expose a predictable method surface: `map`, `filter`, `each`, `reduce`, `fold`, `find`, `any`, `all`, `none`, `sorted`, `sortedBy`, `distinct`, `take`, `skip`, `zip`, `flatten`, `flatMap`, `chunk`, `window`, `group`, `groupBy`, `sum`, and `contains`.

Callback arity, callback parameter compatibility, and callback result type are checked statically. `filter`, `any`, `all`, and `none` require boolean callbacks. `find` returns an Option-like result rather than introducing null.

Text, map, and set values expose smaller predictable extension surfaces documented in `docs/NATURAL_SAGA_0.29.md` and checked by the same type checker.

## 7. Desugaring principle

Natural syntax should reuse existing semantic concepts wherever possible:

- pipeline -> ordinary call;
- trailing block -> closure argument;
- method collection syntax -> typed extension invocation;
- bare first assignment -> inferred immutable lexical binding;
- bare arguments -> ordinary call.

New domain-specific grammar must not be added where a library plus closure/call composition can express the same intent clearly.

## 8. Compatibility and migration

Legacy functional collection calls remain accepted in this preview. The linter emits migration guidance, and `saga migrate` rewrites only conservative code spans. String literals and comments are never migration targets. Any removal requires an explicit edition/major-version migration policy rather than silent reinterpretation.

## 9. Conformance boundary

A conforming Natural Core 0.29 implementation must agree on parsing, binding mutability, closure capture/result behavior, callback type checking, pipeline lowering, same-line bare-call disambiguation, implemented extension-call semantics, and stable diagnostics required by the conformance inventory. The release corpus is intentionally executable in both the Python and independent Go implementations. A binary that only implements the 0.28 grammar is not Natural Core 0.29 conforming. Corpus agreement is necessary evidence, not a substitute for broader differential testing or formal semantics.

## 10. Static and dynamic contract boundary

Natural syntax does not weaken the Standard Core type rules. Function values use contravariant parameter compatibility and covariant result compatibility. Standard generic containers remain invariant; value-level contextual construction may accept safe scalar widening without changing container variance.

`any` is a dynamic boundary, not an escape hatch from declared contracts. When a value crosses from `any` or a hosted/native source into a concrete Saga type, the runtime re-checks the concrete contract. This includes typed bindings, mutable typed bindings, fields, callable signatures where runtime signature metadata exists, and concrete generic type variables inferred for a generic function invocation.

A failure at this boundary is a Saga type diagnostic (normally `SAGA-T103`), never a raw host-language type exception. Runtime generic substitution is required so a contract such as `T` inside `fn f[T](value: T)` is checked against the concrete type inferred for that invocation when a dynamic value crosses into it.


## 11. Preview postfix propagation

The Python reference implementation also implements the Edition 2027 Preview postfix `?` operator documented in `SAGA_LANGUAGE_EDITION_2027_PREVIEW.md`. It is intentionally described here as a preview feature rather than silently reclassifying it as Natural Core 0.29.

For `result[Ok, Err]`, `value?` unwraps `ok(value)` and immediately returns `err(error)` from the nearest callable boundary on failure. The enclosing callable must itself return a compatible `result[..., Err]`. For `option[T]`, `value?` unwraps `some(value)` and immediately returns `none()` on absence; the enclosing callable must return `option[...]`.

```saga
fn load() -> result[int, text] {
    let value = readValue()?
    return ok(value)
}
```

`?` is not a host exception shortcut. It is checked statically and uses Saga `return` semantics, so normal `finally` execution and callable boundaries are preserved. The scalar C AOT profile rejects it fail-closed. The independent Go Standard frontend implements the same propagation case and is differentially checked. Standard native bundles therefore package `?` together with the Natural Core 0.29 syntax supported by the common frontend profile.
