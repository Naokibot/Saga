# Saga 0.39.0 review report

## Scope

0.39 adds a first-class hosted drone flight-control profile on top of Saga's general machine-control layer. The review focused on control-law correctness boundaries, flight-mode versus hard-stop safety semantics, protocol framing, deterministic SITL, Python/Go parity, and preventing the default project template from energizing real actuators.

## Code changes reviewed

### Flight-control stack
- Added the `drone` standard module to both the Python reference implementation and the independent Go implementation.
- Added complementary gyro/accelerometer/magnetometer attitude estimation for deterministic reference/SITL use.
- Added quaternion attitude control as the primary attitude path, angular-rate PID, position/velocity control, and a simpler Euler-angle controller for education/reference use.
- Added normalized Quad-X motor mixing with bounded/desaturated outputs.
- Added geofence containment and predictive breach checks, waypoint missions, RTL planning, and landing descent/flare helpers.

### Flight safety
- Added explicit arming/pre-arm state and health inputs for estimator, positioning, battery, RC link and data link.
- Split failsafes into two classes: controlled HOLD/RTL/LAND retains actuator-control authority; hard DISARM/E-stop trips the shared machine `SafetyLatch` and suppresses control output.
- Automatic policy selects LAND for critical estimator/position/battery conditions and RTL when navigation remains healthy after geofence/link-loss events.
- Failsafe state is latched and requires explicit reset.

### Flight protocols
- Added MAVLink 2 framing, X.25 CRC with CRC_EXTRA, signed-frame generation/verification, 48-bit timestamp handling, replay-floor rejection and HEARTBEAT helper.
- Added DroneCAN classic-CAN message identifiers, CRC-16-CCITT-FALSE, single-frame encoding/decoding and multi-frame transfers with data-type-signature CRC, SOT/EOT, alternating toggle bit and transfer-ID.

### Developer experience
- Added `saga new <name> --template drone`.
- The starter is SITL-first and opens no motor, ESC, CAN, serial or sensor device by default.
- Added drone examples and a dedicated source-bound qualification harness.

## Defects found and fixed during review

1. **Controlled RTL initially tripped the shared machine safety latch.** This made a requested RTL impossible because the same latch disabled actuator control. Fixed by separating controlled flight-mode failsafes from hard DISARM/E-stop paths and adding `control_allowed()` distinct from `flight_allowed()`.
2. **Quaternion regression caught a Python-only constant-name error.** A local `D(2)` reference was invalid. Replaced with the explicit `Decimal(2)` value and added sign-equivalence coverage (`q` and `-q` describe the same attitude).
3. **MAVLink qualification originally claimed replay enforcement without exercising a stale packet.** The qualification now verifies a valid signed frame and separately requires rejection when the minimum accepted timestamp is advanced.
4. **A stale direct signing helper was redundant and fail-only.** Removed it so there is one canonical signed-frame path rather than an ambiguous dead API.
5. **DroneCAN initially covered only single-frame payloads.** Added protocol-level multi-frame CRC/tail/toggle handling and independent regression coverage in Python and Go.
6. **Runtime qualification documentation still described nursery GC as STW-only.** Corrected the evidence text to match the 0.38 incremental nursery implementation while retaining the synchronous compatibility API boundary.

## Regression evidence before final source freeze

- Drone Python regression: 16/16 PASS.
- Drone Go regression: PASS; Go vet PASS.
- Core language group: 70 tests + 6 subtests PASS.
- Module/machine group: 41/41 PASS.
- Native Runtime/Aggregate GC group: 24 tests + 4 subtests PASS.
- Native Codegen/Object group: 13/13 PASS.
- Security group: 12/12 PASS.
- Python self conformance: 48/48 PASS.
- Go self conformance: 48/48 PASS.

A broad combined Python run exceeded the execution window before completion; no fabricated full-suite aggregate is claimed from that run.

## Safety and evidence boundary

No physical aircraft, propeller, ESC, flight controller, IMU, GNSS receiver, barometer, magnetometer, RC link or battery system is attached to this environment. The 0.39 rotational and translational SITL models are deterministic control/dynamics exercises, not a validated aerodynamic airframe model. The complementary estimator is not represented as a production EKF. Saga remains hosted soft real-time and this release is not an airworthiness, SIL/PL, DO-178C, DO-254, or autopilot certification artifact.

Native Runtime ABI remains 0.35 and runtime feature level remains 0.38; 0.39 is a language/library/profile release rather than a native-runtime ABI break.

## Source-bound candidate result

After the first 0.39 source freeze, the dedicated drone qualification passed 12/12, Python<->Go differential passed 48/48, module conformance passed 14/14, Native Runtime passed 10/10, Native Codegen passed 17/17, machine qualification passed, internal security audit reported 0 issues, specification lint passed, Python self-conformance passed 48/48, Go self-conformance passed 48/48, and Go package tests/vet passed. This report update is included in the source tree and therefore the release is refrozen and the source-bound set rerun before packaging.
