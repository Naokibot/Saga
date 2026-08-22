# Saga Go 0.13.0 — Standard Core second implementation

This directory contains a technically independent implementation of the **Saga Standard Core 0.10 candidate profile**. It has its own lexer, parser, Unicode 15.1 identifier tables, static checker, arbitrary-precision exact-number runtime, collection model, generics, object/interface/abstract-class model, exceptions, `option[T]`, higher-order functions, source-unit loader, and isolated task runtime. It does not call or import the Python reference implementation.

The hosted standard-library adapters (GUI, HTTP, database, image/video, cloud, Python plugins, etc.) are intentionally outside the Standard Core claim and remain implementation-specific Hosted Standard facilities.

Build:

```bash
go build -o saga-go ./cmd/saga-go
```

Run the independent Standard Core cross-implementation suite from the repository root:

```bash
python conformance/go_standard_core.py
```

Passing this suite is evidence for the cases represented by that suite, not an ISO/IEC certificate. Formal conformance requires the published profile and an independent test process.
