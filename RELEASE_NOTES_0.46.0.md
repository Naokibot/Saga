# Saga 0.46.0 — Precision Machine Control

Saga 0.46 strengthens machine control without turning the language into a vendor-specific automation DSL.

The release adds one shared Saga source model across the Python reference implementation and independent Go implementation:

- two-degree-of-freedom PID with measurement derivative, derivative filtering, feed-forward, output limits and back-calculation anti-windup;
- explicit motor feed-forward (`kS + kV + kA`);
- alpha-beta position/velocity observer;
- second-order resonance notch filter;
- Clarke, Park and inverse-Park transforms;
- common-mode-centred SVPWM duty calculation;
- hosted execution-budget observation for periodic control work.

The design keeps control mathematics easy to compose while preserving explicit authority at the physical I/O boundary. Controller, observer and filter state are ordinary managed Saga values. CAN, PWM, motor and other device handles remain capability/lifetime-managed resources.

This profile does not claim hard-real-time gate-driver operation, certified functional safety, or physical HIL qualification. Those boundaries remain explicit.
