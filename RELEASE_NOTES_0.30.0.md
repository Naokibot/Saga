# Saga 0.30.0 release notes — Natural Module Core Preview

Saga 0.30.0 adds a common namespaced module and separate-interface model to the Natural language surface.

Implemented in both the Python reference implementation and the independent Go implementation:

- leading `module name` declarations;
- `public` / `internal` top-level visibility with internal-by-default semantics;
- `use "file.saga" as alias` namespaced imports;
- qualified nominal types such as `m.User`;
- qualified inheritance and runtime class resolution;
- canonical module aliases (`SAGA-P109` on conflicting aliases);
- rejection of public APIs that leak internal or dependency-alias nominal types (`SAGA-T118`);
- project-root-aware source graphs using `saga.toml`;
- deterministic Saga Module Interfaces (`.smi.json`);
- public ABI and build hashes;
- dependency ABI invalidation;
- fresh-interface type checking with stale-interface source fallback;
- atomic, hash-verified interface artifacts;
- common Python/Go ABI serialization.

Legacy module-less source units remain available as flattened compatibility units, so projects can adopt namespaces incrementally.

The separate-compilation claim in 0.30 is deliberately scoped: importers can type-check against a fresh public module interface without re-typechecking the implementation body, and dependency ABI changes control invalidation. Saga 0.30 does not yet claim a general native object-file linker or package-distributed precompiled implementation bodies.

See `spec/SAGA_MODULE_CORE_0.30.md`, `docs/MODULES_0.30.md` and `docs/DIFFERENTIATION_0.30.md`.
