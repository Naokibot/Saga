# Saga 0.6.0 Validation Report

Date: 2026-08-07

## Validated host

- OS: Debian GNU/Linux 13 (trixie)
- Kernel: Linux 6.18.35
- Architecture: x86-64
- Python: CPython 3.13.5
- Unicode database: 15.1.0
- Go: 1.23.2 linux/amd64

## Results

| Area | Result |
|---|---|
| Python implementation unit/integration tests | 63/63 passed |
| Python/Go differential conformance | 13/13 passed |
| Standards evidence event-chain verification | passed |
| API compatibility snapshot self-check | passed |
| Linux x86-64 native installer | installed, launched, and uninstalled successfully |
| Installed Python CLI | `Saga 0.6.0` |
| Installed Go CLI | `Saga Go 0.6.0` |
| Embedded wheel digest verification | passed |
| Othello self-play after installation | passed (`OTHELLO_SELFPLAY_OK 61 63 0`) |
| Linux ARM64 installer | cross-compiled and ELF format-checked only |
| Windows x86-64 installer | cross-compiled and PE32+ format-checked only |
| Windows ARM64 installer | cross-compiled and PE32+ format-checked only |

## Standardization readiness

Implemented in software:

- evidence-backed proposer, leader, expert, P-member, adoption, laboratory and market-evidence registry;
- consent templates and SHA-256 sealed evidence records;
- append-only hash-chained audit log;
- technically independent Go core implementation;
- normative isolated-task memory model;
- Unicode 15.1 XID/NFC identifier profile;
- compatibility and change-control policy;
- conformance manifest, differential runner and independent-lab handoff package.

Not established by this validation:

- consent of an eligible ISO/IEC proposal sponsor;
- appointment and consent of a real Project Leader;
- commitments from international experts or P-members;
- real multi-country and multi-organization adoption;
- execution and signature by an independent test laboratory;
- externally sourced market evidence;
- ISO/IEC acceptance, registration, approval or publication.

## Limitations

No Windows host, ARM64 host, macOS host, mobile device, independent laboratory, National Body or external standards committee was available in this environment. Cross-compilation and internal testing do not replace target-platform or third-party verification.
