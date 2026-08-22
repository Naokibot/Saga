# Saga 0.46.0 review — precision machine control

## Findings addressed

1. **Basic PID was too small for precision servo work.** The promoted `pid2` path adds setpoint weighting, derivative-on-measurement, derivative filtering, feed-forward and back-calculation anti-windup while retaining the existing simple PID for beginner use.
2. **Setpoint derivative kick was avoidable.** PID2 differentiates the measurement path, so a setpoint-only step does not itself create a derivative impulse.
3. **Velocity estimation had a large complexity jump.** The existing Kalman facilities remain available, but `alpha_beta` now provides a compact position/velocity observer for cases that do not justify a matrix estimator.
4. **Mechanical-resonance conditioning was missing from the common surface.** A resettable transposed-direct-form-II notch stage is now shared by Python and Go.
5. **FOC primitives were not first-class Saga operations.** Clarke/Park/inverse-Park and common-mode-centered SVPWM are now portable algorithmic functions rather than requiring application-specific foreign code.
6. **Timing statistics and timing policy were too easy to conflate.** `deadline_budget` only observes computation time. It does not stop a motor or change mode; the reaction remains explicit in Saga source.
7. **Control math must not imply hardware authority.** None of the 0.46 algorithmic functions opens a device. Existing physical I/O keeps its explicit capability boundary.
8. **Implementation drift risk.** Every promoted 0.46 function is represented in both the Python reference checker/runtime and the independent Go checker/runtime, with same-source regression coverage.
9. **Example mutability error found during review.** The precision-servo example initially declared its loop counter with immutable `let`; the checker rejected the assignment and the example was corrected to explicit `var`.

## Design review

The release intentionally does **not** add a giant `servo_axis(...)` policy object. The recommended program structure is visible composition:

trajectory → observation → feed-forward → feedback → optional resonance filter → explicit physical output → timing observation.

This follows Saga's design principle that advanced functionality should remain readable rather than becoming a specialist sub-language.

The new stateful controllers are also not promoted to move-only hardware resources. They are control-state values; deterministic ownership rules remain focused on resources where double ownership or implicit lifetime is dangerous.

## Remaining boundaries

- The Python reference path keeps decimal state arithmetic where practical; transcendental coefficient/trigonometric operations cross an explicitly approximate boundary.
- The independent Go machine runtime uses its existing finite `float64` internal numeric path and converts results back to Saga numeric values. Differential tests cover promoted examples, but do not prove bit-identical behavior for every possible input.
- Hosted scheduling and `deadline_budget` are not hard-real-time guarantees.
- The FOC functions are mathematical transforms only. They do not configure ADC synchronization, dead time, gate-driver protection, current sensing or hardware shutdown.
- No physical motor, drive, PLC, encoder or safety certification was performed by this software-only release.
