# Saga 0.38.0 — Incremental Nursery + Qualification Hardening

Saga 0.38.0 converts the nursery/minor collector from a whole-cycle stop-the-world pass into an incremental mark/sweep cycle when low-pause mode is enabled. The synchronous `saga_gc_collect_minor()` API remains available as a compatibility wrapper, while allocation-triggered nursery work is advanced in bounded object-budget polls.

This release also adds reproducible simulation/qualification harnesses for external gates that cannot be physically executed in the build environment: Windows/macOS target binaries are cross-built and structurally inspected; PLC/UART/CAN/servo/motor/encoder behavior is exercised through OS-level pseudo devices and a hardware-in-the-loop digital twin; the real Saga HTTP registry is loaded by concurrent virtual users; and functional-safety pre-certification checks run deterministic/randomized fault campaigns.

None of those simulations are relabeled as physical OS execution, real industrial hardware evidence, public-Internet adoption, or SIL/PL certification.
