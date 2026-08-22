# Saga 0.6.0 Language Review Report

## Corrected defects

1. Network permissions now understand `host:port`; a port-specific grant no longer permits another port.
2. Subdomain access requires an explicit wildcard such as `*.example.com`; suffix coincidences are rejected.
3. HTTP redirects are checked against capabilities at every destination and proxies are disabled by default.
4. Environment variables and cloud SDK use require separate capabilities.
5. Annotation processors require the explicit `--unsafe-processor` acknowledgement.
6. Native and user functions validate argument count at runtime.
7. Private fields are protected at runtime and omitted from reflection.
8. Decimal statistics, vector operations, matrix multiplication and linear regression use Saga's requested decimal context instead of binary float conversion.
9. Ragged matrices are rejected.
10. ORM writes no longer commit an enclosing transaction; database values are decoded to declared Saga types.
11. Nested transactions use savepoints.
12. Duplicate annotations are rejected and unresolved inferred mutual recursion requires explicit result types.
13. Exact integer conversion rejects fractional values instead of truncating silently.
14. HTTP request/response sizes and cryptographic input lengths are validated.
15. External processes are started only with `--allow-process`, never through a command shell, and have a timeout and output limit.

## Verification

- 60 automated tests passed.
- 10 candidate conformance tests passed.
- Othello AI self-play reached a legal terminal state.
- Linux x86-64 machine smoke tests passed for exact numerics, files, SQLite, TCP, UDP, WebSocket, AES-GCM, external processes, images and video.
- GUI startup and event-loop scheduling passed under Xvfb.

## Important unresolved items

- only one implementation family exists;
- no native compiler, package manager or user-module resolver;
- no complete Unicode normalization/confusable policy;
- concurrency semantics are not yet normative;
- adapters are not uniformly resource-contained;
- no Windows/macOS/mobile/physical-IoT machine was available for this validation;
- no independent security audit, fuzzing campaign or formal proof has been completed.
