# Saga Native Object Core 0.31

Status: Preview implementation contract.

## 1. Scope

Native Object Core defines the build/link boundary used by `--profile object` for a Natural Module Core program. It supplements Natural Module Core 0.30; it does not change source-language expression, type, visibility or namespace semantics.

## 2. Native object artifact

Each loaded Saga source unit SHALL be represented by an independently emitted host relocatable object. The object SHALL have a stable virtual source identity and SHALL NOT require an absolute build-machine source path at runtime.

A Standard-profile object MAY contain runtime-consumed checked source/IR data rather than direct target instructions for every Saga operation. If so, tooling SHALL identify the lowering mode and SHALL NOT describe the artifact as full direct machine-code lowering.

## 3. Module identity and ABI

For a namespaced module, its object manifest SHALL record the public ABI SHA-256 defined by the Saga Module Interface. For every direct namespaced dependency, the manifest SHALL record the dependency ABI used to validate that object.

Changing only a dependency implementation while preserving its public ABI SHALL NOT require rebuilding an unchanged importer object. Changing a direct dependency public ABI SHALL invalidate an importer object.

## 4. Object cache integrity

A cache hit is valid only when:

- the object key equals the key recomputed from source/ABI/edge/target/toolchain inputs; and
- the stored object SHA-256 equals the current object bytes.

Failure of either condition SHALL be a cache miss, never an accepted stale object.

Writers sharing one build directory SHALL serialize publication of module objects, startup state, link state and the final build report, or provide an equivalent transactional mechanism. A concurrent build SHALL NOT observe a partially published object/manifest pair as a valid cache hit.

## 5. Runtime archive

The Standard runtime archive SHALL be fingerprinted independently of application objects. Its fingerprint SHALL cover the runtime/compiler source used to build it, Saga implementation version, host target and toolchain identity. Concurrent creation of one cache entry SHALL be serialized or otherwise race-safe.

## 6. Startup object

A startup object SHALL reference each selected source/module object's native symbols and pass the resulting object graph to the Standard runtime entrypoint. The startup cache SHALL depend on graph shape and runtime ABI/header identity, but SHALL NOT need rebuilding solely because a module implementation payload changed without changing its virtual identity.

## 7. Incremental link

The final link key SHALL cover, in deterministic order:

- runtime archive digest;
- startup object digest;
- every linked Saga object digest;
- target/linker identity;
- entry identity.

If the key and existing output digest match the previous build state, the linker MAY be skipped. Otherwise the final output SHALL be generated through a temporary path and atomically replace the destination only after a successful link.

## 8. Fail-closed behavior

Type/check errors, missing toolchains, stale/corrupt ABI information, object digest mismatches, unsafe symlink paths and output/input collisions SHALL fail before replacing a previously valid final executable.

## 9. Portability claim

An implementation SHALL distinguish implemented code paths from physically qualified hosts. The 0.31 reference evidence qualifies Linux x86-64 on the recorded toolchain; other hosts remain unqualified until the same native-object qualification is executed there.
