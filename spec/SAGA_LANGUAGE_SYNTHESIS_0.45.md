# Saga Language Synthesis Profile 0.45

Status: Preview extension shared by the Python reference implementation and the independent Go implementation.

## 1. Purpose

Saga 0.45 promotes a small set of previously uneven Edition 2027 facilities into a common hosted-language surface. The profile deliberately combines useful ideas from established languages without changing Saga into a compatibility dialect of any of them.

The design goals are:

- Python-like low ceremony;
- Ruby-like readable scoped code;
- Go-like structured lifetime and concurrency boundaries;
- Rust-inspired explicit single-transfer ownership for native resources without requiring a general borrow checker;
- Swift/Kotlin-style `async` / `await` source structure;
- preservation of Saga exact values, static contracts, capability checks, `option` / `result`, module ABI and managed-memory defaults.

This profile does not add raw pointer arithmetic, JavaScript null semantics, unconstrained runtime metaprogramming, implicit thread sharing, or a general C/C++ memory model.

## 2. Contextual words

`async`, `await`, `defer`, `using`, `taskgroup`, and `move` are contextual words. They acquire special meaning only in the syntactic positions defined below. Existing source may continue to use those spellings as ordinary names where no profile construct is being parsed.

Examples that remain valid:

```saga
fn await() -> int = 20
fn move() -> int = 22
let async = await() + move()
```

This rule is normative for source compatibility in 0.45. Prefix uses of `await`, `move`, and statement-form `defer` take their operand on the same source line; a contextual word at a delimiter/operator or at the end of a line remains an ordinary name. This makes cases such as `print(await)`, `defer = value`, and an expression body ending in a parameter named `await` unambiguous.

## 3. Asynchronous functions and `await`

An asynchronous function is declared with `async fn`:

```saga
async fn load(id: int) -> text {
    return "item:" + text(id)
}
```

If its declared result is `T`, a call to the function has type `future[T]`. Inside the function body, `return` continues to be checked against `T`, not `future[T]`.

`await expression` requires `expression` to have type `future[T]` and has type `T`. Failure produced by the asynchronous computation is propagated through the normal Saga runtime diagnostic/error mechanism.

An async function call schedules isolated work; it does not make arbitrary mutable caller state shared between agents. Existing Send/isolation rules continue to apply to task APIs and host boundaries.

## 4. `taskgroup`

A `taskgroup` is a lexical structured-concurrency boundary:

```saga
taskgroup {
    first()
    second()
}
```

Async Saga calls created while the group is active belong to the innermost active group. Leaving the block waits for the group's outstanding computations. If the block exits because of a failure, pending group futures are requested to cancel and the original failure is preserved unless a more fundamental runtime failure prevents cleanup.

`taskgroup` is a lifetime/join construct; it is not a shared-memory thread primitive.

## 5. `defer`

`defer expression` registers `expression` for execution when the current lexical callable/block scope exits. Multiple deferred expressions execute in last-in, first-out order.

Deferred work executes on normal fallthrough, `return`, and exceptional/error exit. If ordinary execution is already failing, cleanup must not silently replace that original failure merely because an additional deferred action fails.

```saga
fn read_value() -> int {
    defer log("leaving")
    return 42
}
```

The same semantics apply inside first-class Saga closures.

## 6. `using`

`using` gives deterministic lifetime to a native resource:

```saga
using pool = task.pool(2) {
    let pending = task.submit(pool, work, 42)
    print(task.await(pending))
}
```

The initializer must be a known resource type (or an intentionally dynamic `any` boundary accepted by the checker). The binding is scoped and immutable. On every block exit the runtime invokes the resource's supported deterministic close/release operation.

`using` complements garbage collection; it does not replace managed memory. Ordinary Saga values remain managed. Native handles that own external resources should use deterministic lifetime when prompt release matters.

## 7. `move`

`move name` performs an explicit single transfer of a move-only native resource binding. After a successful move, reading the original binding is a static error when detectable and a runtime error if it reaches execution through a dynamic path.

```saga
var pool = task.pool(1)
task.shutdown(move pool)
pool = task.pool(1) // reinitializes mutable ownership
task.shutdown(move pool)
```

0.45 intentionally restricts this rule to known native/resource types. It does not impose affine ownership on ordinary integers, text, lists, class values, closures or other managed Saga values, and it is not a general Rust-compatible borrow checker.

## 8. Module ABI

For the common `.smi.json` module ABI, a public async function or method declared as returning `T` is serialized with public return type `future[T]`.

Python and Go implementations must compute the same canonical export representation and public ABI hash for otherwise equivalent source.

## 9. Interaction with existing Saga rules

- Exact integer/decimal/rational semantics are unchanged.
- `option[T]`, `result[T,E]`, `?`, records, enums, classes, interfaces and generics are unchanged.
- Hosted operations remain capability-gated.
- Namespaced module visibility and ABI leak rules remain in force.
- `unsafe` remains an explicit boundary; this profile does not expand it.
- The 4 kHz hosted-control profile from Saga 0.44 is retained and remains soft real-time unless separately qualified on an RTOS/driver/hardware path.

## 10. Conformance minimum

A 0.45 common implementation must demonstrate at least:

1. `async fn` call type `future[T]`;
2. `await future[T] -> T`;
3. rejection of assigning a future directly to `T`;
4. taskgroup join before lexical exit;
5. LIFO defer on normal and return paths;
6. defer inside first-class closures;
7. deterministic `using` cleanup;
8. single-transfer `move` and use-after-move rejection;
9. mutable-resource reinitialization after move;
10. contextual-keyword backward compatibility;
11. common Python/Go async module export and ABI-hash agreement.

Passing a finite conformance corpus is evidence for the declared profile, not proof of equivalence for every possible program or host scheduler.
