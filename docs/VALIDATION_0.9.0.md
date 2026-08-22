# Saga 0.9.0 validation report

Date: 2026-08-07

## Host used for executed validation

- Debian GNU/Linux 13 (trixie)
- Linux 6.18.35, x86-64
- CPython 3.13.5
- Go 1.23.2 linux/amd64

Target binaries were additionally cross-built for Linux ARM64, Windows x86-64 and Windows ARM64. Cross-built format validation is not target-hardware execution.

## Results

| Validation | Result |
|---|---|
| Python unittest suite | 119 / 119 passed |
| Standard Core generated report | 119 passed, 0 failed/errors/skips |
| Portable Core candidate suite | 13 / 13 passed |
| Python / Go PCL1 differential suite | 13 / 13 passed |
| Saga self-conformance | 12 / 12 passed |
| Random malformed source smoke | 100,000 cases; unexpected host exceptions 0 |
| Random generated expression execution | 25,000 cases; unexpected host exceptions 0 |
| Go implementation tests | passed |
| Go `vet` | passed |
| Go Race Detector | passed |
| Native installer Go tests | passed |
| Native installer Race Detector | passed |
| Source examples | 6 / 6 static checks passed |
| Standard project templates | 9 / 9 standard lint passed |
| LSP protocol integration | initialize + UTF-16 position encoding + publishDiagnostics + shutdown passed |
| LSP detailed diagnostic | `SAGA-T101` / category `SAGA-T001` verified |
| Unicode project name | Japanese XID/hyphen name passed |
| Project name above old length ceiling | 200 Unicode scalars passed |
| Malformed UTF-8 | controlled `SAGA-L104` lexical diagnostic |
| Non-NFC identifier | controlled `SAGA-L105` lexical diagnostic |
| Bidi control outside string | controlled `SAGA-L106` lexical diagnostic |
| Linux x86-64 installer `--check-only` | passed |
| Linux x86-64 real isolated install | passed |
| Installed `saga --version` | Saga 0.9.0 |
| Installed `saga-go --version` | Saga Go 0.9.0 |
| Installer post-install self-conformance | passed |
| Installed detailed diagnostic | `SAGA-T101` verified |
| Installed LSP command | present |
| Linux x86-64 uninstall | passed; custom prefix removed |
| Linux ARM64 installer | ELF AArch64 format verified; not executed on ARM64 hardware |
| Windows x86-64 installer | PE32+ x86-64 format verified; not executed on Windows |
| Windows ARM64 installer | PE32+ ARM64 format verified; not executed on Windows ARM64 |
| Final public ZIP CRC validation | source, standardization, installer, conformance-lab ZIPs passed |
| Final public SHA-256 manifest | all listed artifacts passed |
| Extracted final source ZIP | 119 / 119 tests and 13 / 13 PCL1 cases passed; Python/Go differential 13 / 13 passed |

## Compatibility result

0.8 -> 0.9 public API snapshot:

- removed public builtins/modules/keywords: none;
- source compatible: yes;
- behavioral/tooling compatibility: intentionally changed;
- reason: structured diagnostics, locale-independent conformance, malformed UTF-8 classification, international project names, removal of the fixed name-length ceiling, and LSP diagnostics.

## Limits of this validation

The following are not claimed:

- Windows runtime execution, Defender or SmartScreen acceptance;
- Linux ARM64 runtime execution;
- macOS execution;
- independent third-party penetration testing;
- independent conformance laboratory certification;
- independent full Standard Core implementation;
- formal ISO/IEC submission, ballot, approval, registration or publication;
- legal/trademark clearance for the name Saga;
- large-scale production workload history.

Project-generated test success is engineering evidence, not external certification.
