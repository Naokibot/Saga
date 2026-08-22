# Saga 0.10.1 Validation Report

## Environment

- Debian GNU/Linux 13, Linux x86-64
- CPython 3.13.5
- Go toolchain available in the validation environment

## Results

| Validation | Result |
|---|---:|
| Python unit/regression suite | 142 / 142 PASS |
| Standard Core runner | 142 / 142 PASS |
| Python embedded self-conformance | 12 / 12 PASS |
| Go embedded Standard Core self-conformance | 10 / 10 PASS |
| Python/Go Standard Core cross suite | 30 / 30 PASS |
| Go `go test ./...` | PASS |
| Go `go vet ./...` | PASS |
| Go Race Detector | PASS |
| Registered Hosted API functions exercised | 149 / 149 PASS |
| Registered Hosted modules | 27 / 27 covered |
| Random parser inputs | 100,000; unexpected host exceptions 0 |
| Random expression executions | 25,000; unexpected host exceptions 0 |
| Internal automated security review | PASS, 0 unreviewed findings |
| Example source checks | 6 / 6 PASS |
| Standard project templates | 9 / 9 PASS |
| Machine smoke: exact numbers | PASS |
| Machine smoke: file + SQLite | PASS |
| Machine smoke: TCP/UDP | PASS |
| Machine smoke: AES-GCM | PASS |
| Machine smoke: process execution | PASS |
| Machine smoke: local WebSocket | PASS |
| Machine smoke: Pillow image | PASS |
| Machine smoke: OpenCV video | PASS |
| Saga Othello self-play | PASS (`OTHELLO_SELFPLAY_OK 61 63 0`) |
| Linux x86-64 final installer end-to-end | PASS |
| Final source ZIP re-extraction | 142/142 tests + 30/30 cross-suite + 149/149 Hosted API PASS |

## Hosted API validation qualification

All 149 registered Hosted API entry points were exercised by `tools/hosted_api_validation.py`. Local/network/storage/UI/media capabilities available in this environment were exercised against real local resources or installed libraries.

The following integrations could not be end-to-end validated against the real external target and were validated at the adapter boundary instead:

- `cloud.call`: botocore Stubber; no live AWS account was used.
- `gpio.*`: API-compatible test double; no GPIO hardware is present.
- `spark.*`: API-compatible test double; PySpark/Spark runtime is absent.
- `game.run_demo`: API-compatible test double because pygame is not installed.

Therefore 149/149 means every registered API entry point was executed and its adapter contract checked; it does **not** mean AWS, physical GPIO, Spark, or pygame themselves were independently validated.

## Host dependency note

`pip check` on the shared execution environment reports an existing `moviepy 2.2.1` / `Pillow 12.2.0` conflict. This is not introduced by Saga's required dependencies; the media libraries are optional adapters in this environment. A clean Saga installation should use an isolated environment and compatible optional dependency set.

## Platform limitation

This report does not claim Windows, Windows ARM64, or Linux ARM64 hardware execution. Those targets require execution on actual target systems. Cross-built binaries alone are not treated as hardware validation.

## Assurance limitation

The security scan and code review reported here are project-internal. They are not a third-party penetration test or independent security audit.
