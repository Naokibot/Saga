# Saga 0.10.1 release notes

0.10.1 is a correctness and general-purpose capability audit release for language draft 0.9.

Highlights:

- exhaustive execution coverage for all 149 registered Hosted API functions;
- runtime validation for native resource types crossing `any` boundaries;
- exact plugin wire semantics for datetime/duration/option;
- host-object leakage hardening and document-store snapshot semantics;
- resource cleanup fixes for image/GPIO/Spark adapters;
- host edge-error normalization;
- Python/Go Set output conformance fix;
- expanded Python/Go Standard Core cross suite (30 cases, including all 62 builtins);
- corrected feature documentation.

No ISO/IEC approval or independent security certification is claimed.
