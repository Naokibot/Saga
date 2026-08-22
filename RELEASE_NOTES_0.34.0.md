# Saga 0.34.0 — Native Aggregate & Managed Heap Preview

Saga 0.34 expands direct native code generation from 0.33 values to aggregate application data.

Highlights:

- payload-bearing `enum` / tagged unions with exhaustive match binding;
- direct-native `list`, `map`, and `set` representations;
- direct-native plain class/object layout, constructors, mutable fields, and methods;
- cross-module aggregate ABI and incremental invalidation;
- a Saga size-class allocator backed by system allocation;
- a single-threaded stop-the-world mark/sweep GC;
- GC tracing through collections, object fields, and managed references stored inside tagged-union payloads;
- common Python/Go tagged-union semantics and common `.smi.json` payload ABI.

0.34 remains a preview. Direct-native inheritance/interface dispatch, concurrent GC, generic aggregate specialization, and managed-reference Option/Result containers remain fail-closed.
