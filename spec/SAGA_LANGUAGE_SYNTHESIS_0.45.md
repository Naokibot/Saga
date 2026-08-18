# Saga Language Synthesis Profile 0.45

Status: Preview extension shared by the Python reference implementation and the independent Go implementation.

## 1. Purpose

Saga 0.45 promotes a small set of previously uneven Edition 2027 facilities into a common hosted-language surface. The profile combines useful ideas from established languages without changing Saga into a compatibility dialect of any of them.

The design goals are Python-like low ceremony, Ruby-like readable scoped code, Go-like structured lifetime/concurrency boundaries, Rust-inspired explicit single-transfer ownership for native resources without a general borrow checker, and Swift/Kotlin-style `async` / `await`, while preserving Saga exact values, static contracts, capability checks, `option` / `result`, module ABI and managed-memory defaults.

This profile does not add raw pointer arithmetic, JavaScript null semantics, unconstrained runtime metaprogramming, implicit thread sharing, or a general C/C++ memory model.

## 2. Contextual words

`async`, `await`, `defer`, `using`, `taskgroup`, and `move` are contextual words. They acquire special meaning only in the syntactic positions defined below. Existing source may continue to use those spellings as ordinary names where no profile construct is being parsed.

```saga
fn await() -> int = 20
fn move() -> int = 22
let async = await() + move()
```

Prefix uses of `await`, `move`, and statement-form `defer` take their operand on the same source line; a contextual word at a delimiter/operator or at the end of a line remains an ordinary name. This makes `print(await)`, `defer = value`, and an expression body ending in a parameter named `await` unambiguous.

## 3. Asynchronous functions and `await`

An asynchronous function is declared with `async fn`. If its declared result is `T`, a call has type `future[T]`. Inside the body, `return` is checked against `T`, not `future[T]`.

`await expression` requires `future[T]` and has type `T`. Async function execution remains isolated hosted work; it does not make arbitrary mutable caller state shared between agents.

## 4. `taskgroup`

A `taskgroup` is a lexical structured-concurrency boundary. Saga async calls created while the group is active belong to the innermost group. Leaving the block waits for its outstanding computations. On failure, pending futures are requested to cancel before the original failure is propagated.

`taskgroup` is a lifetime/join construct, not a shared-memory thread primitive.

## 5. `defer`

`defer expression` registers `expression` for execution when the current lexical callable/block scope exits. Multiple deferred expressions execute last-in, first-out. Deferred work runs on fallthrough, `return`, and error exit. The same semantics apply inside first-class Saga closures.

## 6. `using`

`using` gives deterministic lifetime to a native resource:

```saga
use task
using pool = task.pool(2) {
    let pending = task.submit(pool, work, 42)
    print(task.await(pending))
}
```

The binding is scoped and immutable. On every block exit the runtime invokes the resource's deterministic close/release operation. `using` complements garbage collection; it does not replace managed memory.

## 7. `move`

`move name` performs an explicit single transfer of a move-only native resource binding. After a successful move, reading the original binding is a static error when detectable and a runtime error if reached through a dynamic path.

```saga
use task
var pool = task.pool(1)
task.shutdown(move pool)
pool = task.pool(1)
task.shutdown(move pool)
```

0.45 intentionally restricts this rule to known native/resource types. It does not impose affine ownership on ordinary managed values and is not a general Rust-compatible borrow checker.

## 8. Common task pool

The common hosted task surface includes `task.pool(workers)`, variadic `task.submit(pool, callable, ...args)`, and `task.shutdown(pool)`. A task pool is a move-only deterministic-close resource. `using` waits for submitted work during cleanup; explicit `shutdown` is also available.

## 9. Module ABI

For the common `.smi.json` module ABI, a public async function or method declared as returning `T` is serialized with public return type `future[T]`. Python and Go implementations must compute the same canonical export representation and public ABI hash for equivalent source.

## 10. Interaction with existing Saga rules

Exact integer/decimal/rational semantics, `option[T]`, `result[T,E]`, `?`, records, enums, classes, interfaces, generics, capability security, namespaced visibility, ABI leak rules, and explicit `unsafe` boundaries are unchanged. Saga 0.44's 4 kHz hosted-control profile is retained and remains soft real-time unless separately qualified on an RTOS/driver/hardware path.

## 11. Conformance minimum

A 0.45 common implementation must demonstrate at least:

1. `async fn` call type `future[T]`;
2. `await future[T] -> T`;
3. rejection of direct future-to-`T` assignment;
4. taskgroup join before lexical exit;
5. LIFO defer on normal and return paths;
6. defer inside first-class closures;
7. deterministic `using` cleanup;
8. single-transfer `move` and use-after-move rejection;
9. mutable-resource reinitialization after move;
10. contextual-word backward compatibility;
11. common task-pool execution;
12. Python/Go public async module export and ABI-hash agreement.

Passing a finite corpus is evidence for the declared profile, not proof of equivalence for every possible program or host scheduler.
