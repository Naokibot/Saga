# Security Policy

## Supported version

Security fixes are developed against the current `main` branch and the most recent release line. Historical release branches are retained for reproducibility and may not receive fixes unless explicitly documented.

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities in a public issue before the maintainers have had a reasonable opportunity to investigate them.

Use GitHub's private security-reporting or repository-owner contact path when it is available. Include:

- affected commit or release;
- a minimal reproduction;
- expected and observed behavior;
- security impact;
- whether credentials, private data, code execution, sandbox escape, or machine-control authority are involved.

Do not include real secrets, access tokens, private keys, or sensitive third-party data in a report.

## Machine-control boundary

Saga's language/toolchain checks are not a substitute for target-specific functional-safety engineering. Reports involving motors, drives, PLCs, drones, fieldbus equipment, GPIO, or other physical actuators should state the hardware and isolation conditions used during testing. Independent E-stop, STO/interlock, watchdog, HIL/WCET, and applicable SIL/PL or regulatory evidence remain deployment responsibilities.
