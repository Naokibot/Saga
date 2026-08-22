# Independent security audit scope — Saga 0.10

This package is prepared for an external security assessor. Completion of this document by the Saga project itself MUST NOT be represented as an independent audit.

## Required independent work

- Review lexer/parser/type checker/runtime for memory/resource exhaustion and unexpected host exceptions.
- Attempt capability bypass for filesystem, network, DB, environment, process and cloud boundaries.
- Attempt Python plugin / annotation-processor sandbox breakout, including Python object-graph introspection and namespace/mount bypasses.
- Review HTTP/WebSocket redirects, proxies, DNS rebinding assumptions and local/link-local destinations.
- Review SQL parameterization, ORM transaction handling and null/option boundaries.
- Review task Send/Process-Send validation, snapshot isolation and race behavior.
- Review private data exposure through display, reflection, serialization and errors.
- Review canonical lock/package reproducibility and tamper handling.
- Fuzz both Python and Go Standard Core implementations and compare diagnostics/output.
- Review installers, PATH mutations, payload hashes and uninstall behavior.

## Evidence requested from assessor

Assessor legal name, named testers, dates, commit/source SHA-256, host images, commands, findings with severity/CWE where applicable, remediation verification, and a signed final report.

## Independence rule

The assessor must be organizationally independent from the implementation work. A project-authored internal review, automated scanner, or model-generated report is not an independent third-party audit.
