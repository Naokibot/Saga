# Standardization Gaps — Saga 0.8.0

Saga 0.8.0 contains a substantially reviewed reference implementation and standardization infrastructure, but it is not registered or approved by ISO/IEC.

## External gates still open

- No eligible National Body, committee, secretariat, or Category A liaison has provided documented sponsorship.
- No real Project Leader consent has been entered in the release registry.
- Five P-member commitments and their expert nominations have not been obtained.
- Multi-country, multi-organization adoption evidence has not been supplied.
- No independent laboratory has executed and signed the conformance report.
- Market relevance evidence is not yet sufficient for a New Work Item Proposal.

## Technical work still open

- The Go implementation is an independent **Portable Core Level 1** implementation, not a complete Core-profile implementation.
- Source-unit inclusion, dependency locking, and deterministic local packages are implemented, but namespaced modules, version solving, signed third-party dependencies, and a public registry are absent.
- `any` needs a fully formalized blame model and foreign-boundary contract specification.
- Generics still lack constraints, variance rules, and separate-compilation semantics.
- Cancellation, scheduling fairness, and async I/O are not standardized.
- Normative minimum ceilings and controlled resource diagnostics are defined; independent implementations still need to demonstrate equivalent behavior under memory pressure.
- The hosted standard-library profile requires additional cross-platform implementations.
- The reference interpreter is not a sandbox against explicitly trusted host plugins.
- Windows binaries are produced, but were not executed on Windows hardware in this environment.
- A stable 1.0 specification requires independent editorial and security review.

## Resolved or materially improved in 0.8.0

- explicit `option[T]` for absent JSON and SQL values;
- class/interface subtype assignment and mandatory explicit `override`;
- run-time contracts at native, user-function, and constructor boundaries;
- exact JSON-number handling, duplicate-key rejection, and private-field exclusion;
- deterministic collection presentation and hashable-key constraints;
- right-associative exponentiation with specified unary precedence;
- stable diagnostic category identifiers;
- automatic closing of tracked host resources;
- formatter, standard linter, project manifest, test runner, and stateful transactional REPL;
- evidence re-hashing and conformance-level recording in the standardization registry;
- independent Go lexer/parser/runtime for Portable Core Level 1;
- differential testing between Python and Go for the declared common subset;
- isolated-task memory model with run-time Send enforcement;
- Unicode 15.1 XID/NFC profile and bidi-control rejection;
- SemVer, RFC, and public-API compatibility procedures;
- source units, deterministic `saga.lock`/`.sagapkg`, stable CLI exit statuses, and vendored Unicode 15.1 identifier tables;
- native Windows and Linux installer builds.
