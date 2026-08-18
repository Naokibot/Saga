# Saga 0.46.0 Validation

Source tree SHA-256: `586e700d07a716bcb516476cf01ad33688a8d05990070cd140b576000d7b6023`

Source manifest SHA-256: `e078014b56a1edd2fe13bdb8e8e027d0483524aee1c2130656d2da9d53ecdd55`

Validation performed against the frozen 0.46 source:

- Precision Machine cross-implementation qualification: 5/5 PASS.
- Machine-control regression: Python 32 tests PASS; Go targeted native regression PASS; Go vet targeted PASS.
- Precision + existing machine/autonomy/fine/4 kHz Python tests: 34/34 PASS.
- Language/Natural/module group: 82/82 PASS.
- Standard/runtime-safety/native-runtime/native-codegen group: 37/37 PASS.
- Module conformance: 14/14 PASS.
- Python↔Go differential validation: 48/48 PASS.
- Python self-conformance: 48/48 PASS.
- Go self-conformance: 48/48 PASS.
- `go test ./... -count=1`: PASS.
- `go vet ./...`: PASS.
- Go race detector for `TestPrecisionMachine046`: PASS.
- internal security audit: PASS, 0 issues reported.
- source-manifest verification: PASS.

Physical machine/HIL qualification remains unexecuted and is not represented as a pass.
