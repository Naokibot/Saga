# Saga 0.47.0 review — advanced motion control

## Findings addressed

1. **0.46 exposed FOC transforms but not a persistent current controller.** 0.47 adds d/q PI current state, PMSM feed-forward/cross-coupling compensation, voltage-vector limiting, anti-windup and scalar duty access.
2. **The older encoder paths split incremental tracking from higher-level observation.** `encoder_integrated` now owns count unwrap, absolute alignment and timestamp-derived velocity in one portable state object.
3. **Online adaptation had no small deterministic primitive.** `rls2` adds fixed-size two-parameter recursive least squares without introducing a general matrix allocation into the source API.
4. **Predictive control was missing between PID/LQR and application-specific code.** `mpc2` adds a bounded 2-state/1-input fixed-horizon controller with fixed horizon/iteration bounds.
5. **Disturbance and friction compensation were being left to application glue.** Explicit DOB and Stribeck helpers make those stages visible and replaceable.
6. **Multi-axis synchronization needed a smaller electronic-gearing primitive.** `axis_sync` exposes ratio/offset correction and skew health without hidden stop policy.
7. **CAN-FD payload support existed but BRS/ESI/timestamp metadata did not have a promoted API.** 0.47 preserves FD flags and timestamp source explicitly.
8. **EtherCAT support needed a clear boundary.** Pure EtherCAT datagram framing is portable; Linux raw-L2 exchange is a capability-gated resource. The release does not call that transport a complete EtherCAT master.
9. **Hardware timestamp requests could be overclaimed.** The receive path reports `hardware` only when raw hardware time is actually present, otherwise it reports software/host fallback.
10. **An MCU/RTOS profile needed compiler semantics rather than documentation alone.** `@control_tick` is now enforced by both Python and Go checkers with matching Saga diagnostic IDs.
11. **Review found a resource-lifetime omission.** The new EtherCAT raw handle was initially capability-gated but absent from the move-only resource-type set. It was added to both implementations so `using`/`move` semantics apply to physical EtherCAT handles while FOC/MPC/observer state remains ordinary managed control state.
12. **Review found a mobile-runtime integration regression.** Adding the Go control-profile checker created a new checker dependency not copied into the embedded mobile Standard Core. `control_profile_047.go` was added to the mobile runtime file set and the 82-test language/module group returned to PASS.

## Design result

The 0.47 layer follows the Saga rule: **control mathematics is easy to compose; authority to affect physical equipment is explicit.** FOC, encoder state, RLS, MPC, disturbance/friction math, synchronization and EtherCAT frame construction can be tested without device permission. Raw CAN/EtherCAT/PWM/device operations remain privileged resources.

`@control_tick` deliberately restricts source semantics rather than pretending the hosted reference runtime is an MCU. It removes explicit dynamic Saga allocation/task/lifetime/exception patterns and requires statically bounded loop syntax. A target backend still has to prove allocator-free lowering and target timing.

## Remaining boundaries

- No physical motor-current loop, gate driver, ADC/PWM synchronization, encoder, CAN-FD adapter or EtherCAT network was operated by this software-only qualification.
- Linux raw EtherCAT transport does not implement topology discovery, mailbox protocols, ENI configuration or Distributed Clocks servoing.
- Host `SO_TIMESTAMPING` support and NIC hardware timestamp capability are environment-dependent; timestamp provenance is therefore reported rather than assumed.
- Python/Go numeric agreement is tested on promoted cases, but the Go implementation's finite floating-point internal math is not a claim of bit-identical decimal behavior for all inputs.
- `@control_tick` is a source-level profile. WCET, no-allocator machine code, interrupt latency and safety certification remain target-specific qualification tasks.
