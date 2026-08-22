# Saga Compiler Self-Hosting Profile 1.0 — Draft

An implementation claiming this profile shall satisfy all of the following:

1. the published official compiler driver source is valid Saga source;
2. a trusted Stage0 implementation can create Stage1 from that source;
3. Stage1 can create Stage2 from the same Saga source without invoking an
   external programming-language compiler;
4. Stage2 can create Stage3 in the same way;
5. Stage2 and Stage3 are byte-identical under the reproducible-build profile;
6. the resulting compiler passes the published Standard Core conformance suite;
7. the installer shall fail closed if the fixed point is not obtained;
8. the bootstrap runtime/kernel and its provenance shall be disclosed separately.

This profile defines **compiler self-hosting**. It does not require the execution
VM, garbage collector, operating-system shim or original seed implementation to
be written in Saga. A stronger all-runtime-source-in-Saga claim would be a
separate profile and is not implied by this document.
