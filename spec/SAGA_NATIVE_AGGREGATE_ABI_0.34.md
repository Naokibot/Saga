# Saga Native Aggregate & Managed Heap ABI 0.34

**Status:** Preview specification  
**Language release:** Saga 0.34.0  
**ABI:** 0.34

## 1. Scope

ABI 0.34 extends the direct native code-generation boundary introduced by ABI 0.32 and the value ABI from 0.33. It adds native representations for user enums/tagged unions, lists, maps, sets, and plain classes/objects, together with the first Saga-owned allocation and garbage-collection policy.

The profile is intentionally fail-closed. Source constructs whose observable Saga semantics do not have a stable 0.34 native representation are rejected before native linking.

## 2. Stable native value representations

### 2.1 Tagged unions

A user enum is nominal. Every enum receives a deterministic 64-bit type id derived from its module-qualified identity. Variants use their declaration index as the discriminant. A variant may carry zero to four payload values in ABI 0.34.

```saga
enum Result {
    Ok(int),
    Err(text)
}
```

`SagaTagged` stores:

- nominal `type_id`,
- variant `tag`,
- payload `arity`,
- payload kind metadata,
- up to four payload slots.

Stable native payload kinds in 0.34 are `int`, `bool`, borrowed UTF-8 `text`, and managed `SagaRef` values. Nested tagged unions, Option/Result payloads, and `unit` payloads are not part of the 0.34 direct ABI.

Declaration order is ABI-significant. The common `.smi.json` representation therefore preserves source variant order and records each variant's payload types.

### 2.2 Collections

`list[T]`, `map[K,V]`, and `set[T]` are managed heap references (`SagaRef`). Their elements are represented by tagged `SagaHeapValue` slots. Heap slots may contain scalar values, text, tagged unions, or managed references.

0.34 defines semantic operations used by the direct backend, including list indexing/update, map lookup/update/removal, set insertion/removal/containment/union/intersection, and collection length.

### 2.3 Objects/classes

A supported class is represented by a managed `SagaRef` with a nominal 64-bit type id and fixed field-slot order. Constructor layout includes private fields because private layout changes affect the native ABI even when the source public field surface is unchanged.

0.34 direct native classes are deliberately limited to plain, non-generic classes without inheritance, interfaces, abstract methods, or virtual dispatch. Methods are ordinary native symbols receiving `SagaRef self` as the leading argument.

## 3. Managed heap

0.34 introduces the first Saga-managed heap runtime.

### 3.1 Allocator

The allocator uses size-class free lists for small and medium allocations and obtains backing blocks from the platform allocator. Reclaimed GC storage is returned to Saga free lists for reuse. Large blocks are returned directly to the system allocator. The runtime exposes live, peak, and reserved byte counters for qualification.

This is a Saga allocation policy backed by system memory allocation; it is not a claim that 0.34 replaces the operating system allocator.

### 3.2 Garbage collector

The 0.34 collector is a **single-threaded, stop-the-world mark/sweep preview**.

Roots are explicitly emitted by native code generation. Root kinds include direct `SagaRef` slots and `SagaTagged` slots. Tagged-union roots are scanned according to their payload kind metadata, so a managed object inside a tagged-union payload remains alive.

Heap tracing follows:

- list/set element references,
- map key/value references,
- object field references,
- tagged-union payload references stored in collection/object slots.

Compiler-generated lexical root marks are unwound on ordinary block exit, `break`, `continue`, and `return`, preventing the GC from retaining addresses of expired C stack slots.

## 4. Match lowering

Payload patterns bind native payload slots directly:

```saga
match result {
    case Result.Ok(value) { print(value) }
    case Result.Err(message) { print(message) }
}
```

The static checker requires exhaustive enum matches unless a default branch exists. Match payload variables are typed from the variant declaration. `_` discards a payload value without creating a binding.

## 5. Separate compilation and ABI invalidation

Native module ABI manifests include:

- enum type ids, tags, and payload types,
- complete class native layout,
- function/constructor/method signatures,
- managed-heap memory model identifier.

A dependency implementation-only change may reuse importer objects when its public/native ABI hash is stable. Variant payload changes, class layout changes, or public signature changes invalidate importer objects.

## 6. Safety boundary

The following are intentionally rejected by the direct 0.34 backend rather than miscompiled:

- class inheritance and interface/virtual dispatch,
- generic classes and generic aggregate ABI,
- nested tagged-union payloads,
- Option/Result containing managed references,
- native exception unwinding for aggregate values,
- concurrent mutation during GC,
- stabilized object/set textual display where the generic heap printer cannot preserve reference-runtime output.

## 7. Concurrency status

The 0.34 GC is not concurrent and is not thread-safe. Hosted/Standard runtime concurrency remains a separate execution profile. Programs requiring concurrent native managed-heap mutation must not use this preview as a production concurrency runtime.

## 8. Compatibility direction

ABI 0.34 is a preview and may evolve before ABI 1.0. The intended next steps are inheritance/interface dispatch, richer generic specialization, owned native text integration, managed Option/Result descriptors, exception unwinding, and eventually a generational/incremental or concurrent collector.
