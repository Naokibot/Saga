# Saga 0.47.0 review — advanced motion control

## Findings addressed

1. 0.46 exposed FOC transforms but not a persistent current controller; 0.47 adds d/q PI state, PMSM feed-forward/decoupling, voltage limiting, anti-windup and SVPWM state.
2. Incremental and absolute encoder paths are unified through unwrap, alignment and timestamp-derived velocity.
3. Fixed-size `rls2` supplies deterministic online identification without a general matrix-allocation API.
4. `mpc2` adds bounded fixed-horizon predictive control between PID/LQR and application-specific code.
5. Disturbance-observer and Stribeck helpers make compensation explicit rather than hidden in application glue.
6. `axis_sync` adds bounded electronic gearing and skew health without hidden stop policy.
7. CAN-FD now promotes BRS/ESI/timestamp metadata rather than exposing only payload capability.
8. EtherCAT framing is portable; Linux raw-L2 exchange is capability-gated and is not called a complete EtherCAT master.
9. Hardware timestamp requests never upgrade fallback time by assertion; timestamp provenance is reported.
10. `@control_tick` is enforced by both Python and Go checkers with matching diagnostics.
11. Review found the EtherCAT raw handle missing from the move-only resource set; both implementations were corrected.
12. Review found the Go control-profile checker missing from the embedded mobile Standard Core file set; the mobile integration was corrected and language/module regressions returned to PASS.

## Design result

**Control mathematics is easy to compose; authority to affect physical equipment is explicit.** FOC, encoder state, RLS, MPC, DOB, friction, synchronization and frame construction remain ordinary testable Saga state. Raw CAN/EtherCAT/PWM/device operations remain privileged resources.

## Remaining boundaries

No physical motor-current loop, inverter/gate driver, ADC/PWM synchronization, encoder, CAN-FD adapter or EtherCAT network was operated by this software-only qualification. Host timestamp capability is environment-dependent. `@control_tick` is source-level; MCU object-code allocation proof, WCET, interrupt latency and safety certification remain target-specific.
