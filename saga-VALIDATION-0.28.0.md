# Saga 0.28.0 validation

## Machine-control profile

- Hosted `machine` API: 69 functions.
- Hosted API validator: 237/237 registered functions covered across 29 modules.
- Python machine-control regression: 16/16 PASS.
- Go machine-control tests: PASS, including race-enabled machine tests.
- Non-destructive machine qualification: PASS.
- Physical machine qualification on this host: UNEXECUTED (no I²C/SPI/UART/PWM/IIO/CAN devices exposed).

## Existing Saga regressions

- Python test collection: 225 tests. All test modules have been executed; 225/225 PASS, including 4 unittest subtests in the standard-language module.
- Go normal regression: PASS.
- `go vet ./...`: PASS.
- Go race detector: all discovered tests pass when executed in bounded groups; the long aggregate runner is not counted when the outer execution harness times out.
- Native game API: 101/101 checker/runtime/manifest alignment PASS.
- Browser host API: 101/101 PASS.
- Universal App Action surface: PASS.
- Defensive security API: PASS.
- Linux x86-64 Native 0.28.0: built as a static ELF and executed successfully.
- Cross-build format checks: Linux ARM64, Windows x86-64/ARM64 and macOS x86-64/ARM64 produced the expected target formats. Cross-builds are not target-host execution evidence.

## SH-3

The monolithic SH-3 validator exceeded the execution harness window and is not counted as a pass. Its gates were executed separately:

- strict C11 bootstrap VM and launcher: PASS;
- compiler Stage2 == Stage3: PASS, SHA-256 `8ea80749c7aba49116742de76cca0168c8b37357fb27b3cbdd000a0739ab12d4`;
- canonical kernel Stage2 == Stage3: PASS, SHA-256 `a71899d4eccd11dc94b035f50c2e1c3cafa220f6a2d23b9fc8642c9a8aaa311e`;
- Standard Core success corpus: 23/23;
- diagnostic corpus: 11/11;
- Edition 2027 Preview corpus: 15/15;
- deterministic SH3IMG1 and run-image: PASS;
- empty-PATH official distribution and self-host compiler: PASS;
- SH-3 source-boundary audit: PASS.

## Boundaries

The following are intentionally not claimed as PASS from this host: physical machine I/O, hard-real-time scheduling, machine-safety certification, Windows/macOS target-host execution, public HTTPS Registry operation, independent security audit, and independent Final-spec approval.
