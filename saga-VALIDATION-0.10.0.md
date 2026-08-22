# Saga 0.10.0 validation report

Environment used for native execution: Debian GNU/Linux 13, x86-64, CPython 3.13.x, Go toolchain available in the release environment.

| Validation | Result |
|---|---|
| Python full unit/regression suite | 135 / 135 passed |
| Python Standard Core candidate suite | 135 / 135 passed |
| Python self-conformance | 12 / 12 passed |
| Go Standard Core self-conformance | 10 / 10 passed |
| Python/Go Standard Core cross suite | 29 / 29 passed |
| Python/Go lock and canonical package test | byte-identical in the cross suite |
| Go unit tests | passed |
| `go vet` | passed |
| Go Race Detector | passed |
| parser fuzz-smoke | 100,000 cases; unexpected host exceptions 0 |
| generated expression execution | 25,000 cases; unexpected host exceptions 0 |
| project internal security scanner | 0 unreviewed findings |
| Python bytecode compile check | passed |
| Linux x86-64 native installer | installed successfully |
| Installed Python self-conformance | 12 / 12 passed |
| Installed Go self-conformance | 10 / 10 passed |
| Installed Python/Go smoke program | both returned 81 |
| Linux x86-64 uninstall | passed |
| Linux ARM64 binary | cross-built; ELF AArch64 format verified; real hardware not available |
| Windows x86-64 binary | cross-built; PE32+ x86-64 format verified; real Windows execution not available |
| Windows ARM64 binary | cross-built; PE32+ ARM64 format verified; real Windows ARM64 execution not available |
| Security regression suite | 9 / 9 passed |
| Final source ZIP extracted Python suite | 135 / 135 passed |
| Final source ZIP extracted Python/Go cross suite | 29 / 29 passed |
| Final source ZIP extracted Go tests | passed |
| Independent third-party security audit | **not performed**; external audit handoff kit prepared |

## Host dependency note

`pip check` on the shared build host reports `moviepy 2.2.1` requiring Pillow `<12` while the host contains Pillow `12.2.0`. Saga Standard Core declares no third-party Python runtime dependency; the conflict is a property of the shared host environment and is recorded rather than hidden.

## Claim boundary

Cross-compiling a Windows/ARM64 executable is not treated as real-hardware validation. Project-authored security analysis is not treated as an independent audit. The provided hardware scripts and audit kit are the handoff needed to close those external evidence gaps.
