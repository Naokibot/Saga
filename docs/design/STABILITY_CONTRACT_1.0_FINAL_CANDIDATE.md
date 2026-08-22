# Saga 1.0 stability contract — Final Candidate

## Compatibility

1. A conforming 1.x implementation must preserve the observable Standard Core
   meaning of a valid 1.0 program unless the specification marks the behavior as
   implementation-defined.
2. New syntax in a minor release must not reinterpret an existing valid token
   sequence.
3. Removal of a public Standard Core feature requires a future major language
   edition.
4. Diagnostic *messages* may improve; diagnostic IDs and categories are the
   machine-stable contract.
5. Package locks identify the language edition and source hashes.
6. Unicode identifier behavior is edition-pinned, not inherited from the host OS.

## Determinism

For programs without explicit concurrency or external Hosted APIs, implementations
must agree on Standard Core output for all specified operations. Concurrency may
leave scheduling order unspecified only where the memory model says so.

## Failure model

Host panics/exceptions must not be exposed as the language contract. Implementations
translate them into Saga diagnostics or documented resource failures.

## Deprecation

Before final publication, experimental features remain outside this contract. Language Edition 1.0 Standard Core enters
the compatibility contract above. Experimental Hosted APIs are versioned
separately so they cannot destabilize the core language.
