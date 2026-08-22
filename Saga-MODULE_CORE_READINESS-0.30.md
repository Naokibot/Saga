# Saga 0.30.0 — Natural Module Core Readiness

## Verdict

Saga 0.30.0 has a real common module boundary in both the Python reference implementation and the independent Go implementation. It is suitable as a **Preview** for managed application/domain/data/automation projects that need multiple namespaces and incremental frontend checking.

It is not yet a claim of a mature native object-module linker or a 1.0 GA ecosystem.

## What is implemented

- `module name` namespaced source units.
- Internal-by-default top-level declarations.
- Explicit `public` and `internal` visibility.
- `use "file.saga" as alias` namespace binding.
- Qualified nominal types (`m.User`) that remain distinct across namespaces.
- Qualified imported inheritance at checker and runtime.
- Project-root-aware source graphs using `saga.toml` in Python and Go.
- Canonical alias enforcement (`SAGA-P109`).
- Public ABI leak prevention (`SAGA-T118`).
- Legacy module-less flattened source units for incremental migration.
- Deterministic common `.smi.json` module interfaces.
- Public ABI hash, source hash and build hash verification.
- Dependency ABI invalidation without invalidating importers for implementation-only changes.
- Fresh-interface type checking with stale/corrupt interface source fallback.
- Atomic interface writes and symlink output/source policy.
- Namespace-preserving Standard standalone bundle embedding.
- Namespace-preserving generated mobile Standard Core runtime.

## Separate compilation boundary

0.30 implements **frontend/interface separate compilation**. A dependency public surface can be compiled into an SMI and an importer can reconstruct/check against that public surface without re-typechecking the dependency implementation when the interface is fresh.

0.30 does not yet distribute precompiled executable module bodies or link independent native object modules. Runtime execution still includes the source implementation body in the selected runtime/bundle.

## Public ABI rule

The 0.30 common ABI intentionally rejects accidental exposure of internal nominal types and direct dependency-alias nominal types. Explicit re-export is reserved for later work. This keeps public ABI serialization independent of local import alias spelling.

## Why this changes Saga's practical scale

Before 0.30, a large Natural project could split files but lacked a common Python/Go namespace + ABI boundary. 0.30 makes it possible to:

- contain names;
- state which declarations are stable public surface;
- keep same-spelling domain types distinct;
- avoid re-typechecking an unchanged dependency ABI;
- detect dependency signature changes deterministically;
- use the same module graph in reference and Go/native execution.

That moves Saga from primarily small/medium flattened source graphs toward realistic medium-size modular projects.

## Remaining 1.0-level gaps

- native object-file / linker-level separate compilation;
- explicit module re-export and package-level module identity;
- hierarchical dotted module declarations;
- package publication of precompiled interface + implementation artifacts;
- incremental code generation and compiler daemon/cache strategy;
- much larger real-world dogfooding repositories;
- long-term compatibility/governance evidence for SMI schema evolution;
- external compiler/security review and independent production qualification.
