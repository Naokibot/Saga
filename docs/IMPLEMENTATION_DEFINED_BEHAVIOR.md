# Saga Python 0.9.0 implementation-defined behavior

- Host runtime: CPython 3.13 or newer.
- Identifier membership: vendored Unicode 15.1 XID tables.
- Identifier normalization: NFC; non-NFC source identifiers are rejected, not silently rewritten.
- Decimal rounding: round-half-even unless an operation explicitly defines another mode. Saga defines no fixed precision ceiling; the host decimal provider may still exhaust resources or expose a finite exponent domain.
- Saga defines no fixed source-byte, token, syntax-depth, AST-node, module-count/depth, package-size, integer-bit, exponent-magnitude, precision, function-arity, worker-count, project-name-length, or execution-step ceiling.
- `--step-limit N` is an opt-in deployment watchdog, disabled by default.
- Text indexing counts Unicode scalar values as represented by Python code points; it does not count grapheme clusters.
- Filesystem case sensitivity, path length, filename encoding, storage capacity, and atomicity follow the host after Saga capability and containment checks.
- Process output currently uses an implementation safety budget; hosted I/O budgets are implementation characteristics and not Saga language limits.
- Task scheduling order and independent task output order are unspecified.
- GUI, media, cloud, IoT, Spark, WebSocket, and advanced cryptography availability depends on optional providers listed by `saga doctor --json`.
- Unsupported diagnostic locales fall back to English. Japanese and English catalogues are bundled.
