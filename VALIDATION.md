# Saga 0.8.0 validation report

Date: 2026-08-07

## Host used for executed validation

- Debian GNU/Linux 13.3 (trixie)
- Linux 6.18.35, x86-64
- glibc 2.41
- CPython 3.13.5
- Go 1.23.2

## Executed results

| Validation | Result |
|---|---:|
| Python unit/integration/standard tests | 96/96 passed |
| Installed-runtime self conformance | 12/12 passed |
| PCL1 candidate conformance cases | 13/13 passed |
| Python/Go PCL1 differential cases | 13/13 passed |
| Go unit tests | passed |
| Go race detector | passed |
| Go vet | passed |
| Native installer Go tests | passed |
| Parser/compiler random-input smoke | 100,000 cases, 0 unexpected host exceptions |
| Generated expression runtime smoke | 25,000 cases, 0 unexpected host exceptions |
| Python compileall | passed |
| Saga example static checks | 19/19 passed |
| Standard project templates | 9/9 passed |
| Reproducible wheel build | two builds byte-identical |
| Reproducible Go linux/amd64 build | two builds byte-identical |
| Deterministic `.sagapkg` | two packages byte-identical |
| Clean virtual-environment wheel installation | passed |
| Installed `saga --version` | `Saga 0.8.0` |
| Installed self conformance | 12/12 passed |
| Go linux/amd64 binary | executed, `Saga Go 0.8.0` |
| Native Linux x86-64 installer check-only | passed |
| Native Linux x86-64 install | passed |
| Native Linux x86-64 post-install checks | passed |
| Native Linux x86-64 uninstall | passed |
| Linux ARM64 executable format | ELF AArch64 verified |
| Windows x86-64 executable format | PE32+ x86-64 verified |
| Windows ARM64 executable format | PE32+ ARM64 verified |

## Existing hosted integration coverage

The inherited and rerun suite covers local HTTP server/client, TCP, UDP, WebSocket, SQLite, ORM transaction rollback, files and binary data, exact JSON, concurrency, AES-GCM provider integration when installed, image/video providers when installed, GUI construction in the available environment, plugin capability checks, and Saga Othello self-play.

## Not executed in this environment

- Windows installer launch, PATH update, uninstall, Defender, SmartScreen, or Authenticode;
- Linux ARM64 execution on physical or emulated ARM64 hardware;
- macOS, iOS, or Android execution;
- Raspberry Pi GPIO hardware;
- real AWS account, Spark cluster, or distributed production database;
- production load, long-duration soak, or adversarial penetration testing;
- independent standards laboratory or third-party security audit.

Cross-compiled file-format checks are not equivalent to target-hardware execution.

## Evidence files

- `validation/standard-core-conformance-0.8.0.json`
- `validation/self-conformance-0.8.0.json`
- `validation/differential-conformance-0.8.0.json`
- `validation/fuzz-smoke-0.8.0.json`
- `validation/compatibility-0.6-to-0.7.json`
- `validation/doctor-0.8.0.json`
- `validation/info-0.8.0.json`
- installer check/install/uninstall logs

## Conclusion

The executed evidence supports release as a reviewed pre-standard candidate. It does not establish ISO/IEC approval, complete cross-platform conformity, production fitness for every hosted module, or independent certification.
