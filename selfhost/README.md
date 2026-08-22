# Saga self-hosted compiler

`selfhost/sagac.saga` is the source of the official Saga compiler driver.

## Fixed-point proof

A release performs the following reproducible bootstrap:

1. Stage0 Saga Native builds Stage1 from `sagac.saga`.
2. Stage1, executing Saga source, builds Stage2 from the same file.
3. Stage2 builds Stage3 from the same file.
4. Stage2 and Stage3 must have identical SHA-256 values.
5. The installed compiler is Stage2, not Stage1.

Run the same proof from a source checkout with:

```sh
saga bootstrap-self .
```

The native installer repeats the fixed-point check on the target system and
fails closed if Stage2 and Stage3 differ.

## What “self-hosted” means here

The compiler program distributed as `sagac` is sourced from Saga and reaches a
reproducible fixed point. It runs on the Saga Native execution kernel. The kernel
(parser/checker/runtime services used to execute Saga code and link standalone
bundles) is a separately audited bootstrap substrate and its current seed source
is retained under `implementations/go/`.

This is the conventional compiler-level self-hosting boundary: the compiler is
written in its own language while the execution VM/runtime may have an
independent implementation. The project deliberately does not call this an
“all runtime source is Saga” claim.
