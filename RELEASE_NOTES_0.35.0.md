# Saga 0.35.0 — Native Runtime ABI Preview

Saga 0.35 completes the next native-runtime layer above 0.34 aggregates.

Highlights:

- direct-native class inheritance, abstract classes and interfaces;
- stable method dispatch slots and linker-visible virtual dispatch wrappers;
- dispatch-graph-aware incremental invalidation;
- managed-reference and owned-text payload tracing for native Option/Result;
- owned immutable UTF-8 `SagaText` integrated with the managed heap;
- GC-safe native `throw` / `catch` / `finally` and catchable native runtime failures;
- `finally` semantics for `return`, `break` and `continue`;
- C `setjmp`/`longjmp` volatile-lifetime correctness for observable local variables and GC roots;
- young/old generations, minor GC, promotion and remembered-set write barriers;
- incremental major marking with mutation barriers and root rescanning;
- optional C11-thread concurrent physical sweep;
- concrete monomorphization of local generic functions and classes, including explicit `Box[int]`-style aggregate annotations.

The collector remains a preview: it is not a concurrent-mark/compacting or hard-real-time GC. Cross-module generic template instantiation, generic inheritance/methods and open-world virtual extension remain fail-closed.
