# Saga 0.36.0 Validation Report

## Measured validation performed during this review

The following inventories were executed on the 0.36 working tree during implementation and review. Final source-bound validators are regenerated after this document is finalized.

### General language regression

A representative general-language inventory covering the core language, Standard/Natural surface, modules/separate compilation, generic relations, full-stack behavior, and machine-control suites passed:

- **129 tests + 6 subtests PASS**.

This is not presented as the complete repository-wide Python test inventory; several long combined invocations exceeded the execution window and are therefore not counted as passes.

### Machine-control regression

- Python machine-control suites (`0.28` + `0.36`): **23 / 23 PASS**.
- Independent Go machine-control tests: PASS.
- Independent Go full test suite: PASS.
- Independent Go `go vet ./...`: PASS.
- All checked Saga machine examples: PASS static checking.
- Simulation-first generated machine project: check and run PASS (`safe= true`).

### Native regression samples

Executed separately to avoid conflating tool timeout with a code failure:

- Native Runtime 0.35 regression: **10 / 10 PASS**.
- Native Aggregate/GC 0.34 regression: **14 / 14 PASS**, plus its subtests.
- Human-Centered/Native Value 0.33 regression: **9 / 9 PASS**.
- Native Codegen 0.32 regression: **8 / 8 PASS**.
- Security regression samples: **12 / 12 PASS**.

### Cross implementation

Pre-final-freeze runs produced:

- Python Self Conformance: **48 / 48 PASS**.
- Go Self Conformance: **48 / 48 PASS**.
- Python ↔ Go common differential: **48 / 48 PASS**.
- Module graph conformance: **14 / 14 PASS**.

The differential/module reports are rerun after the final source manifest is regenerated so the distributed evidence is bound to the exact source tree.

### Fuzz / static review

During the 0.36 review line:

- parser fuzz: **100,000 cases**;
- expression fuzz: **25,000 cases**;
- unexpected host exceptions: **0**;
- internal automated security audit: PASS with 0 reported issues on the reviewed tree before the last source-binding refresh;
- specification review lint: PASS before the last source-binding refresh.

Those source-bound checks are rerun after the final manifest freeze.

### Portable builds

Manual `CGO_ENABLED=0` Go builds for the maintained implementation passed for:

- Linux amd64;
- Linux arm64;
- Windows amd64;
- macOS amd64;
- macOS arm64.

A cross-build is compilation evidence, not physical execution evidence.

## Physical machine evidence boundary

The review host did not expose representative I2C, SPI, UART, PWM, IIO, CAN, motor-drive, encoder, or Modbus field equipment. Therefore physical-machine qualification is explicitly **UNEXECUTED** rather than inferred from simulation or compilation.

No hard-real-time or functional-safety certification claim is made.
