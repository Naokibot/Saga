# Depth without ceremony

Saga deliberately combines a small surface syntax with architectural tools found
in languages such as Java and C-family ecosystems.

| Need | Small Saga program | Larger Saga program |
|---|---|---|
| Values | inferred `let` | explicit types and immutable contracts |
| Reuse | function | generic function / interface |
| Data + behavior | plain values | class, private state, inheritance |
| Missing data | `option[T]` | domain-specific option pipelines |
| Errors | clear runtime diagnostic | typed boundaries + exceptions |
| State | local `var` | encapsulated mutable field or closure cell |
| Parallel work | `task.spawn` | isolated worker architecture |
| Distribution | `saga run` | lock, verify, pack, standalone build |
| Compiler | installed `sagac` | fixed-point self-host rebuild |

The language does not equate depth with verbosity. Advanced features remain
available but are introduced only when the program's design needs them.
