# Saga 0.12.0 differentiation summary

Saga combines a small beginner-first surface with exact-by-default arithmetic, static contracts, explicit absence (`option[T]`), lexical closures, deny-by-default hosted capabilities, reproducible signed packages, an independent second Standard Core implementation, safe third-party bridges, and portable runtime-AOT compilation.

The most unusual combination is **capability-transparent packages**: registry metadata carries a static minimum capability set, `saga capabilities` shows authority before execution, package versions/hashes are pinned, and publishers can sign the exact canonical package bytes. Existing Python libraries can be surfaced only through an explicit function allowlist inside the isolated bridge rather than being imported directly into the Saga process.

See `docs/DIFFERENTIATION_0.11.md` for trade-offs and comparison rationale.
