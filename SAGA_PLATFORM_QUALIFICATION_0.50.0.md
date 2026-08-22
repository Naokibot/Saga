# Saga 0.50.0 platform qualification statement

Saga 0.50 Production GA separates **language/toolchain release qualification** from **machine deployment qualification**.

## Release-qualified software paths

- Python reference compiler/runtime regression on the qualification Linux host.
- Independent Go implementation full tests and `go vet`.
- Go race detector on the changed control paths.
- Direct-native Saga control program build, byte-reproducibility and execution on the qualification Linux host.
- Deterministic cross-compilation performed by `tools/build_release.sh` for supported native distribution targets.

## Non-claims

Cross-compiling a Windows/macOS binary is not treated as physical target-host execution evidence. The Production GA language/toolchain label also does not imply target-specific hard-real-time, WCET, CAN/EtherCAT/PWM edge timing or functional-safety certification for a physical machine. Those are deployment gates enforced separately by `production-check --machine`.
