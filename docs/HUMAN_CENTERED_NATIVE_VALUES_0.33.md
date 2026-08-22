# Human-Centered Saga and Native Values — 0.33

Saga 0.33 combines two constraints that should reinforce rather than fight each
other: code should read naturally to the programmer, and the implementation
should preserve exact static/runtime contracts underneath that surface.

## Natural, not merely short

`unless condition { ... }` exists for cases where the negative condition is the
way a person naturally states the rule. It is not a second control-flow model;
the parser normalizes it to `if not condition`.

`enum` and exhaustive `match` let programs name states instead of encoding them
as numbers or chains of unrelated booleans. Missing enum variants are diagnosed
with `SAGA-T112` before execution.

```saga
enum Status { Ready, Running, Done }

match status {
    case Status.Ready   { prepare() }
    case Status.Running { update() }
    case Status.Done    { finish() }
}
```

Public enums are nominal types. `a.Status` and `b.Status` are different types
even if they have identical variant names. `.smi.json` records public enum
variants so separate compilation preserves that identity and exhaustiveness.

## Programmer happiness without dynamic ambiguity

The design direction is inspired by the broad Ruby tradition of optimizing a
language for human readers and writers. This is not a claim of endorsement by
Yukihiro Matsumoto, and Saga deliberately does not copy Ruby's dynamic type or
runtime-metaprogramming semantics.

Saga's version of programmer happiness is progressive depth:

- first assignments can infer immutable bindings;
- trailing closures and bare calls enable readable library DSLs;
- static types become explicit when they communicate useful boundaries;
- modules, capabilities and ABIs remain strict even when surface syntax is light;
- sugar lowers to a small semantic core instead of multiplying runtime models.

## Native Value ABI 0.33

Direct codegen now carries borrowed UTF-8 text, option and result values across
module object boundaries without the Go Standard Runtime. `?` is lowered to a
native early-return branch. C clients can use the generated `.nabi.h` structs
and linker-visible symbols directly.

Owned text, native enum layout, objects/classes, closures and collections remain
fail-closed until their lifetime/layout ABIs are defined. This is intentional:
a pleasant surface should not be paid for with hidden undefined behavior.
