# Saga 0.9 internationalization profile

## Source and identifiers

- Source encoding is UTF-8.
- Identifier membership is frozen to the vendored Unicode 15.1 XID profile for the Saga 0.9 language edition.
- Identifiers must already be NFC-normalized; implementations do not silently rewrite them.
- Bidi control characters are rejected outside string literals.
- Identifier comparison is case-sensitive and locale-independent.

The fixed Unicode edition is deliberate: upgrading the host language or operating system must not silently change whether an existing Saga source file is accepted. A future Unicode profile update requires a Saga language-edition change and regenerated conformance data in each implementation.

## Locale-independent semantics

The operating-system locale shall not change:

- decimal syntax or arithmetic;
- identifier matching;
- keywords;
- source ranges;
- JSON numeric serialization;
- deterministic core sorting rules;
- conformance outcomes.

Locale may affect only diagnostic prose and explicitly locale-aware hosted APIs.

## International project names

Saga 0.9 permits NFC Unicode project names using the same XID safety profile, with hyphen-separated components. Path separators, dots, empty components, bidi controls and non-XID characters are rejected. Saga specifies no fixed project-name length; host storage exhaustion is an implementation characteristic. This removes the previous ASCII-only project-name restriction without reintroducing package path traversal.

Examples:

```toml
[project]
name = "学習ツール-日本"
version = "1.0.0"
language = "0.9"
entry = "main.saga"
```

## Diagnostics

The reference implementation bundles English and Japanese. English is the fallback language for international tooling and draft-standard review. Machine-readable conformance never depends on translated text.

## Accessibility

Diagnostics remain complete when colour is disabled. Severity, source range and repair information are available as text and in JSON/SARIF rather than being conveyed solely through terminal styling.
