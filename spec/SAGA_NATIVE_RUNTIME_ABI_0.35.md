# Saga Native Runtime ABI 0.35

**Status:** Preview specification  
**Language release:** Saga 0.35.0  
**Native ABI:** 0.35

## 1. Scope

ABI 0.35 extends the 0.34 managed aggregate ABI with six runtime facilities that share one native object/lifetime model:

1. class inheritance, interfaces and virtual dispatch;
2. GC-described managed `option[T]` and `result[T,E]` payloads;
3. owned immutable native UTF-8 text;
4. exception unwinding integrated with GC roots and `finally`;
5. generational collection, incremental major marking and concurrent sweeping;
6. native monomorphization of generic functions and aggregate classes.

Unsupported combinations fail during native code generation instead of falling back to another runtime.

## 2. Inheritance, interfaces and virtual dispatch

A class keeps a deterministic 64-bit nominal type id. A derived class begins with the complete base-field layout and appends its own fields, so base field offsets remain stable inside the closed application graph.

Every method contract has a deterministic dispatch slot derived from the method name, parameter ABI types and result ABI type. Public class/interface ABI records include the slot plus a linker-visible virtual-dispatch symbol. A virtual entry accepts `SagaRef self`, reads its runtime type id, and selects the most-derived implementation. Direct method symbols remain available for concrete ABI entries.

The 0.35 dispatch model is **closed-world stable-slot/type-id dispatch**. The native object cache key includes a digest of the complete class/interface dispatch graph; hierarchy/override changes therefore invalidate objects whose generated wrappers depend on that graph. This is not an open-world plugin-vtable ABI.

Interfaces and abstract classes are nominal contracts. Concrete classes must provide compatible implementations for inherited abstract/interface methods. Override parameter/result ABI types are invariant in this preview.

## 3. Managed Option and Result

`SagaOption` and `SagaResult` remain compact tagged native values, but payload roots now carry an explicit payload-kind descriptor. The collector can trace a managed `SagaRef` or owned `SagaText` selected by an option/result tag.

Supported direct payload kinds include scalars, text, enums and managed aggregate references. The compiler emits typed roots for option/result locals and temporaries before assigning potentially managed payloads.

Direct nesting of option/result inside another option/result, or storing option/result directly inside a generic heap slot, is still rejected because 0.35 heap slots do not yet carry recursive tagged-value descriptors.

## 4. Owned native text

`SagaText` is:

```c
typedef struct {
    const uint8_t *data;
    uint64_t len;
    SagaRef owner;
} SagaText;
```

`owner == NULL` denotes borrowed/static storage. An owned string points to an immutable managed heap text object through `owner`. The runtime provides owned copy, concatenation and scalar-to-text conversion. Text roots trace `owner`; reclaiming the owner reclaims its byte storage.

ABI calls never infer ownership from a raw pointer. Ownership is represented by the explicit owner reference.

## 5. Exception ABI and GC-safe unwind

Native exceptions use `SagaException { kind, message }` and a linked `SagaExceptionFrame` containing a C `jmp_buf`, the GC root mark active at entry and the previous frame. `throw` stores an owned message, unwinds roots to the target frame and transfers control with `longjmp`.

Runtime failures that occur while an exception frame is active are raised as `NativeFailure`, so arithmetic/runtime diagnostics can be caught without host-process undefined behavior.

Compiler-generated user bindings that can be observed after `longjmp` are emitted with the C `volatile` requirements needed by `setjmp`/`longjmp`. GC root entries likewise retain volatile-qualified slot addresses.

`finally` runs on:

- normal completion;
- explicit `throw` and native runtime failure;
- `return`;
- `break`;
- `continue`.

A `finally` body executes outside the exception frame of the corresponding protected body, so an exception raised by cleanup propagates outward instead of being caught again by the same try.

## 6. Generational and incremental GC

The managed heap has young and old generations. Minor collection traces roots and the remembered set; surviving young objects age and are promoted after the configured survival threshold. Mutating an old object with a young reference records the object in the remembered set.

Major collection is incremental mark/sweep:

- starting a major cycle marks current roots and pushes them onto a gray stack;
- `saga_gc_step(budget)` scans at most the requested gray-object budget;
- roots are rescanned on every step, providing the root write barrier for incremental mutation;
- object-field/collection mutation during marking shades a newly referenced object when the container is already marked;
- allocations during an active major cycle start marked so they cannot be reclaimed by that cycle.

After marking, dead objects are detached from the managed heap synchronously. When C11 threads are available, physical `free()` of the detached dead list may run on a background sweep thread. Allocator/GC accounting is updated before handoff, so the worker does not mutate allocator counters concurrently with the mutator.

This is **generational GC + incremental major marking + concurrent sweep**. It is not a fully concurrent tracing, compacting, parallel or hard-real-time collector.

## 7. Generic monomorphization

Local generic top-level functions and local generic classes are specialized to concrete native ABI types. Type arguments may be inferred from call/constructor arguments or stated explicitly on aggregate bindings such as `Box[int]`.

Every specialization receives:

- a deterministic concrete nominal identity for a generic class;
- a deterministic specialization suffix on native symbols;
- separately specialized field layouts and method/function signatures;
- a distinct type id for each concrete generic aggregate.

Specialization discovery runs to a fixed point so emitting one specialization may discover another local specialization.

0.35 deliberately rejects cross-module generic-template specialization, generic inheritance and generic methods. These require a package-level template-instantiation/ownership policy beyond the local 0.35 monomorphization boundary.

## 8. ABI metadata and incremental invalidation

Native `.nabi.json` records identify:

- ABI/language version 0.35;
- `managed-ref-generational-incremental-concurrent-sweep-0.35` memory model;
- `closed-world-stable-slot-type-id-switch` dispatch model;
- base class and implemented interfaces;
- complete native class layout;
- direct and virtual method symbols plus dispatch slots;
- generic template descriptors and emitted concrete specializations where applicable.

The build cache additionally hashes the resolved dispatch graph so implementation-only changes can remain local while hierarchy/layout/dispatch contract changes rebuild affected native objects.

## 9. Safety boundary

The following remain fail-closed in this preview:

- open-world/dynamically loaded subclass extension of a linked dispatch graph;
- generic inheritance;
- generic methods;
- cross-module generic template instantiation;
- recursively descriptor-bearing option/result values stored directly inside aggregate heap slots;
- production claims of lock-free, compacting, concurrent-mark or real-time GC behavior.

These boundaries are explicit ABI limits, not silent fallback paths.
