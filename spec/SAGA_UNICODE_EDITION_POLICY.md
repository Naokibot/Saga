# Saga Unicode Edition Policy

1. Source encoding is UTF-8.
2. Identifier start/continue tables, normalization rules and security exclusions are pinned per Saga edition.
3. A compiler shall not silently reinterpret an old edition under a newer Unicode database.
4. Identifiers must be NFC; non-NFC spellings are diagnosed, not silently normalized.
5. Bidi formatting controls are rejected outside string data.
6. An implementation shall report the exact vendored Unicode profile through `saga info`.
7. Updating Unicode data is an edition/evolution change with generated-table provenance and cross-implementation conformance vectors.

Saga Native 0.18 keeps the audited vendored 15.1 profile for compatibility. This policy makes later table upgrades explicit rather than host-dependent.
