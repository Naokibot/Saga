# Saga 0.7 conformance plan

1. Run `saga conformance --json` for an installed-runtime self-check.
2. Run `python conformance/run.py` for the PCL1 candidate suite.
3. Run `python conformance/go_standard_core.py` to compare Python and Go Standard Core behavior, diagnostics, source-unit handling, lockfiles, and canonical package bytes.
4. Run `python conformance/standard_core.py` for the full project test mapping.
5. Build the lab handoff with `python conformance/package_for_lab.py`.
6. An independent organization shall verify hashes, rebuild both implementations, execute the suite on at least two operating systems, record deviations, and sign its own report.

Project-generated reports are development evidence, not independent certification.
