# Saga 0.24.1 feature audit

## Language

Language Edition 1.0 RC1 and Edition 2027 Preview remain available: static typing/inference, exact numbers and explicit floats/fixed integers, closures, OOP/interfaces/generics/associated types, enums/records/match, option/result propagation, exceptions, resource/move/using/defer, structured concurrency, derive/comptime, modules and Diagnostics v2.

## Defensive cybersecurity

- 11-function Native `security` surface aligned with the Python Hosted security profile for common names.
- SHA-512, HMAC-SHA256, constant-time comparison and cryptographic random bytes.
- PBKDF2-HMAC-SHA256 password storage primitives with bounded verification cost.
- AES-GCM authenticated encryption/decryption through `crypto`.
- streaming file SHA-256, IP/CIDR checks, X.509 certificate metadata and certificate-verifying TLS probe.

## Persistence safety

The built-in application KV transaction profile now provides cross-process writer serialization for cooperating Saga processes on Unix/Windows and disk-revision optimistic conflict detection. It remains a small application KV store, not a replacement for PostgreSQL/SQLite-class relational database semantics.

## Application / browser / game

- `app`: 10 Saga source APIs; 53 first-party Browser Universal App operations.
- `web`: 107 functions / 101 Browser Host operations.
- `game`: 101 typed APIs including portable 2D and CPU 3D baseline.
- Real Chromium 144 Blink/V8 validation retained.

## Toolchain and self-hosting

The normal run/check/build/test/fmt/lint/repl/debug/lsp/lock/verify/pack/registry/capability/learning/conformance/doctor/info toolchain remains present. Official SH-3 compiler and canonical kernel are Saga source and retain byte-identical Stage2/Stage3 fixed points under split qualification.

## Boundaries

- Internal security review is not a third-party penetration test.
- Hardware/vendor operations are not marked qualified without the relevant target environment.
- Mobile source/runtime generators exist, but signed device/store qualification still requires Xcode/iOS and Android SDK/NDK/device environments.
- GPU/AAA 3D and a complete OS/kernel SDK remain larger ecosystem profiles rather than claims of this release.
