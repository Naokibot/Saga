# Saga Native Object + Incremental Build Guide — 0.31

## Build

```bash
saga build main.saga --target native --profile object
```

Optional controls:

```bash
saga build main.saga --target native --profile object \
  --build-dir .cache/saga-native \
  --output build/app

saga build main.saga --target native --profile object --force
```

The default cache is:

```text
<project>/.saga-build/native-object/<host-target>/
```

Important files:

```text
objects/*.o                 native relocatable source/module objects
objects/*.native.json       content/ABI/object manifests
objects/startup.o           native startup/registry object
interfaces/*.smi.json       cached public module interfaces
runtime/<fingerprint>/*.a   Standard Core native runtime archive
state.json                  link input/output digest state
last-build.json             human/tool-readable last-build summary
```

## What is compiled separately?

Each source unit is assigned a stable virtual identity. A source unit object contains:

1. native registration functions used by the startup object;
2. UTF-8 Saga source bytes;
3. resolved import-edge metadata using virtual identities rather than build-machine paths;
4. object metadata carrying source/ABI identity.

The host compiler emits a real relocatable object and the host linker consumes that object. The final executable calls the linked Go Standard Core runtime through a C ABI and supplies the linked module graph.

This preserves the complete Standard Core without pretending that the current backend directly machine-code-lowers every language feature.

## Cache invalidation

A module object key includes:

- Saga implementation/language profile version;
- host target;
- virtual module/source identity;
- source SHA-256;
- own public ABI SHA-256 when namespaced;
- direct dependency public ABI SHA-256 values;
- resolved dependency edges;
- C compiler identity.

This gives the desired separate-compilation behavior:

```text
change private implementation in dependency
  -> dependency object rebuild
  -> importer object reuse
  -> relink

change public dependency ABI
  -> dependency object rebuild
  -> importer object invalidated/rebuilt
  -> relink

change nothing
  -> all objects reused
  -> runtime reused
  -> startup reused
  -> link skipped
```

The reference checker still validates the loaded graph before native linking. Thus an incompatible public API change fails before the existing good executable is replaced.

## Runtime archive cache

The Standard Runtime archive fingerprint includes the non-test Go runtime/compiler sources, `go.mod`, Saga implementation version, host target, Go identity and C compiler identity. The archive build is serialized with a cross-process file lock.

The build directory itself is also protected by a cross-process incremental-build lock. Object/manifest publication, startup state and final link state therefore form one serialized cache transaction when multiple build processes target the same cache.

## Security properties

- object and runtime cache files are digest checked;
- link output is temp-written and atomically replaced;
- runtime archive generation is locked and atomically committed;
- custom build directories may not traverse user-controlled symlinks;
- output symlinks are rejected;
- output collisions with source/compiler/runtime/object inputs are rejected;
- final binary/object payload uses virtual file identities and does not require source paths at runtime.

## Qualification

Run:

```bash
python tools/native_object_qualification.py --output validation/native-object-0.31.0.json
```

It verifies first build, complete cache hit, implementation-only invalidation, ABI invalidation, execution, native relocatable object format and same-host/toolchain reproducibility.
