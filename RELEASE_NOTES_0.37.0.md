# Saga 0.37.0 — Open-World Runtime & Industrial Reliability Preview

## Highlights

- Added bounded low-pause major GC polling with incremental mark and sweep.
- Replaced closed-world native virtual dispatch with an open-world runtime registry.
- Added public native type-id and dispatch-slot constants for extension modules.
- Added cross-module specialization for public generic functions and generic classes.
- Strengthened Python and Go debugger/profiler workflows with watches, bounded JSON recording and statement profiles.
- Added SQLite FTS5 trigram registry indexing with a fallback backend and 100k synthetic scale qualification.
- Added Windows/macOS cross-platform target-build and target-test compilation qualification.
- Added accelerated 168-hour industrial digital-twin endurance testing with following-error, soft-limit, E-stop, Modbus CRC and timeout fault injection.

Native Runtime ABI remains **0.35** because the release is additive/compatible rather than a layout break. This release does not relabel simulation or cross-compilation as physical qualification.
