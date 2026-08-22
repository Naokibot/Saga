# Saga C Core

A clean-room C11 implementation of a deliberately limited Saga Standard Core subset, written without importing or linking the Go Native or Python reference implementation. It exists to demonstrate that the normative specification is implementable by another codebase and to catch specification ambiguities.

Current conformance coverage is 11 seed cases: C001-C006 and C010-C014. OOP/private-access/exception execution (C007-C009) are explicitly not implemented here and must not be inferred from this subset result. This is technical implementation independence, not organizational independence or third-party certification.

Build: `cc -std=c11 -O2 -Wall -Wextra -Werror -o saga-c-core saga_c_core.c`
Run: `python3 run_conformance.py`
