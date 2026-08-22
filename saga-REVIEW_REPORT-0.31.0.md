# Saga 0.31.0 Native Object / Incremental Link Review

## Review objective

Turn Natural Module Core 0.30 frontend/interface separate compilation into a real host object/link boundary without regressing Standard Core semantics.

## Findings addressed

1. Standard standalone 0.30 used one runtime bundle/payload and had no per-module linker objects.
2. A no-change application build could skip a bundle rebuild, but it could not reuse/link at module object granularity.
3. Dependency ABI changes had no native-object invalidation model because native module objects did not exist.
4. A shared runtime archive needs independent caching and cross-process serialization.
5. Object/output cache artifacts require digest checks and collision/symlink protection.
6. Qualification evidence must snapshot each build phase; re-reading a mutable `last-build.json` after later builds produced misleading historical evidence and was fixed in the qualification tool.
7. Per-artifact atomic writes alone did not make a shared incremental build directory transactional across processes; a build-directory cross-process lock now serializes object/startup/link state publication.
8. The 0.30 current-release API validators referenced release snapshots that had never been materialized; 0.31 compatibility snapshots are now explicit and revalidated against the unchanged hosted surfaces.

## Implemented response

- real host relocatable object per source unit;
- native registration code in each module/source object;
- source + resolved-edge + ABI metadata payload;
- C-callable Go Standard Runtime static archive;
- startup registry object;
- host native linker final step;
- direct dependency ABI invalidation;
- object/runtime/startup/link digest caches;
- no-change link skip;
- atomic output state;
- cache tamper detection;
- symlink/output collision rejection;
- reproducibility qualification;
- cross-process shared-cache transaction serialization;
- current-release API compatibility snapshot validation.

## Important boundary

The Standard object backend is a **runtime-object backend**. The `.o` files are real native linker inputs and contain native registration code, but the complete Saga program semantics are still implemented by the linked Standard Runtime. This review does not re-label that as per-function direct machine-code AOT. The checked scalar backend remains the direct C lowering profile.
## Review outcome

The 0.31 object backend now has a real host-linker boundary, ABI-aware incremental invalidation, no-change compile/link skipping, cache integrity verification, and serialized shared-cache publication. The full Python unittest inventory is **348 / 348 PASS** when the final Platform/Evidence group is included; Go tests, both 44-case self-conformance implementations, fuzz and native-object qualification also pass.

The claim remains deliberately narrower than full direct native code generation: Standard Core module objects carry verified runtime payload plus native registration code and execute through the linked Go Standard Runtime archive.

