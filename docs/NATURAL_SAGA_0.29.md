# Natural Saga 0.29 Design

## Goal

Saga 0.29 moves the language surface toward one rule: **code should reveal the programmer's intent before it reveals compiler ceremony**. The entry level is intentionally small, while explicit types, classes, capabilities, native resources and systems profiles remain available when they carry information a reader actually needs.

The 0.29 work is a language-design preview, not a GA or standards claim. It deliberately distinguishes implemented reference semantics from features that still require parity work in the independent/native implementations.

## Decisions implemented in the reference frontend

### Natural bindings

```saga
name = "Saga"
```

The first bare assignment in a scope introduces an **immutable** binding. Reassignment is rejected. Mutation stays explicit:

```saga
var count = 0
count = count + 1
```

This keeps the beginner spelling short without making mutation implicit.

### First-class trailing closures

```saga
users.filter { it.active }
values.fold(0) { total, value -> total + value }
```

A one-parameter contextual closure receives `it`. Two or more parameters must be named explicitly. The block's final expression is its result, and `return` exits the closure itself rather than an enclosing function. A closure used without a contextual function type is zero-argument by default; parameterized stored closures can use an explicit `fn[...]` type when inference has no parameter context.

```saga
greet = { print("Hello") }
let double: fn[int, int] = { value -> value * 2 }
```

Control-flow body braces win over trailing-closure shorthand, so ordinary calls remain natural:

```saga
if ready() { start() }
```

If a control-flow condition itself uses a trailing closure, parenthesize the condition to make the intent explicit:

```saga
if (values.any { it > 0 }) { print("positive") }
```

### Collection methods

The reference runtime and checker now understand method-oriented collection operations including `map`, `filter`, `each`, `fold`/`reduce`, `find`, `any`, `all`, `none`, `sorted`, `sortedBy`, `distinct`, `take`, `skip`, `zip`, `flatten`, `flatMap`, `chunk`, `window`, `group`, `groupBy`, `sum`, and `contains`.

Old functional forms such as `filter(predicate, values)` remain accepted during the transition. `saga migrate` rewrites only cases it can prove safe.

### Optional pipeline

```saga
result = values
    |> filter { it > 0 }
    |> map { it * 2 }
    |> distinct
    |> sorted
```

`|>` is syntactic sugar over ordinary calls and typed collection extension calls. It does not introduce a second execution model. Legacy callback-first pipeline stages remain compatible, including the historical middle collection position used by `reduce` and `find`.

### Library-defined DSLs

Bare arguments are allowed when the first argument is on the same line as the callee. This enables small library DSLs without adding domain-specific grammar:

```saga
fn panel(title: text, body: fn[unit]) {
    print(title)
    body()
}

panel "Todo" {
    print("inside")
}
```

Ambiguous unary-looking forms such as `f -1` are intentionally *not* bare calls; write `f(-1)`. This rule exists because subtraction must remain unsurprising.

## Safety model

Conciseness does not override the existing rules for immutable `let`, private fields, type-checked callbacks, exact arithmetic, capability-gated native resources, Option/Result, and isolated tasks. Contextual closure types are checked at compile time. For example, `values.filter { it + 1 }` is rejected because the predicate must return `bool`.

## Orthogonality

The new surface is implemented using a small number of reusable concepts:

1. bare binding is assignment plus first-definition semantics;
2. trailing blocks are first-class lexical closures;
3. method collection APIs are library/runtime extensions over existing collection values;
4. pipeline is call sugar;
5. bare DSL arguments become ordinary `Call` AST nodes.

No separate "beginner language" or "DSL language" is introduced.

## Native/compiler boundary

The scalar C AOT backend accepts natural first-assignment bindings for its supported **checked int64/bool deployment subset**. It traps integer overflow and modulo-by-zero, preserves left-to-right evaluation where lowered, and rejects exact rational division or other Standard semantics it cannot preserve. Saga identifiers are mangled before C emission, so valid Saga names are not constrained by C keywords. The full Go Standard Core implementation from 0.28 does **not** yet implement the complete Natural 0.29 syntax. Therefore a 0.28 Go/native binary must not be presented as 0.29 language-conforming evidence merely because it builds older Saga programs.

The next parity milestone is to implement the same closure, call-sugar, extension-call and binding semantics in the independent implementation, add differential cases, and only then promote the native profile to 0.29 conformance.

## Design rules used for further work

- Humans First.
- Natural over merely short.
- Simple things simple; complex things possible.
- Safe by default; mutation and authority explicit.
- Fast by default, but no performance claim without measurement.
- One concept, one pattern.
- Errors should teach the repair.
- Tools are part of the language.
- Beginner-friendly and expert-powerful must be the same language.
- Abstraction must not force avoidable runtime cost.
- Freedom without chaotic spelling.
- Code should reveal intent.
