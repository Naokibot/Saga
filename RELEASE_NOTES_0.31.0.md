# Saga 0.31.0 release notes — Native Object + Incremental Link Preview

Saga 0.31 turns the 0.30 module/interface boundary into a real host-linker boundary for Standard Core native builds.

## New native object profile

```bash
saga build src/main.saga --target native --profile object
```

The object profile now produces:

- one real host relocatable object (`.o` on the validated Linux path; `.obj` is selected on Windows) for every loaded Saga source unit;
- native registration code and a path-independent validated Saga payload inside each object;
- an object manifest containing source SHA-256, public module ABI SHA-256, direct dependency ABI hashes, resolved dependency edges, target/toolchain identity and object SHA-256;
- a cached Go Standard Core runtime as a C-callable static archive;
- a native startup object that references each module object's symbols;
- a final executable produced by the host native linker.

The full Standard Core semantics still execute through the linked Standard Runtime. This is therefore a **runtime-object backend**, not a claim that every Saga function is directly lowered to target machine instructions. The scalar AOT backend remains the direct checked C/machine-code subset.

## Incremental compile and link

Object reuse is content- and ABI-addressed:

- unchanged source + unchanged direct dependency ABIs -> module object cache hit;
- dependency implementation-only change with stable public ABI -> importer object remains a cache hit;
- dependency public ABI change -> importer object is invalidated;
- changed object input -> final native link reruns;
- completely unchanged object/runtime/startup input set -> final link is skipped and the existing output digest is verified.

The runtime archive has its own toolchain/source fingerprint and cross-process build lock. Module objects, runtime metadata, startup object metadata, build state and output replacement use atomic or temp-then-replace writes.

## Reproducibility and safety

On the validated Linux x86-64 environment, two clean builds in different cache directories with the same source and toolchain produced byte-identical module objects and byte-identical final executables.

Object and output cache entries are SHA-256 verified. A tampered object is regenerated. Build/output paths reject user-controlled symbolic-link redirection, and the final output may not overwrite source files, module objects, the startup object, compiler executables or the runtime archive.

## Validation boundary

0.31 is validated on the available Linux x86-64 host using Go 1.23.2 and Clang 17. The object/link orchestration contains platform-aware naming and C ABI boundaries, but this release does **not** claim physical Windows/macOS qualification for the new object profile until those hosts execute the same qualification suite.

See `spec/SAGA_NATIVE_OBJECT_CORE_0.31.md`, `docs/NATIVE_INCREMENTAL_BUILD_0.31.md`, and `saga-VALIDATION-0.31.0.md`.
