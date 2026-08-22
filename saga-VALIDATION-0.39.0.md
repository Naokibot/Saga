# Saga 0.39.0 validation

## Drone-specific regression

The dedicated `tests/test_drone_control_039.py` suite contains 16 checks covering estimator behavior, Euler and quaternion attitude paths, angular-rate and position control, mixer bounds, geofence prediction, missions, controlled and hard failsafes, RTL/landing, MAVLink framing/signing/replay rejection, DroneCAN single/multi-frame transport, and Saga source-level bindings.

The independent Go implementation has a separate drone test group covering the same main safety/protocol/control paths.

## Deterministic SITL qualification

`tools/drone_control_qualification.py` executes source-bound checks including:
- Python and Go drone regressions;
- the SITL-first project template and examples;
- a 3-axis quaternion attitude + angular-rate loop with an injected angular-rate disturbance;
- a local-Cartesian position/velocity loop with acceleration limits;
- controlled RC/data-link loss -> RTL without a machine hard trip;
- hard DISARM -> shared machine safety trip;
- geofence prediction and RTL phase behavior;
- MAVLink 2 signed-frame verification plus stale-timestamp replay rejection;
- DroneCAN reference CRC, single-frame layout, and multi-frame SOT/EOT/toggle behavior.

The rotational/position models are intentionally deterministic and simplified. They are useful to catch sign, saturation, state-machine and protocol regressions; they are not aerodynamic qualification.

## Existing subsystem regression

Before final source freeze:
- core language: 70 tests + 6 subtests PASS;
- module/machine: 41/41 PASS;
- Native Runtime/Aggregate GC: 24 tests + 4 subtests PASS;
- Native Codegen/Object: 13/13 PASS;
- security: 12/12 PASS;
- Python self conformance: 48/48 PASS;
- Go self conformance: 48/48 PASS;
- Go package tests/vet: PASS.

The complete combined Python discovery run exceeded the execution-window limit and therefore is not reported as a fresh all-suite PASS.

## Physical qualification status

Physical flight: **UNEXECUTED**.

No physical sensor, ESC/motor/propeller, radio, autopilot board, GNSS, battery, CAN bus or serial flight hardware was connected. The default `drone` template intentionally performs no physical actuator output.

## Source-bound final set

After the review documents are complete, a 0.39 source manifest is frozen and the following are rerun against that exact tree: drone qualification, Python<->Go differential conformance, module conformance, Native Runtime qualification, Native Codegen qualification, machine qualification, internal security audit, specification lint, self-conformance, Go tests/vet, and clean-extract reproduction from the distribution ZIP.

## Source-bound candidate result

The first complete 0.39 candidate produced: drone 12/12, Python<->Go 48/48, module 14/14, Native Runtime 10/10, Native Codegen 17/17, machine PASS, internal security 0 issues, specification lint PASS, Python self-conformance 48/48, Go self-conformance 48/48, and Go package tests/vet PASS. Because this validation text is itself release source, the final distribution is refrozen after this addition and the same source-bound checks are rerun against the final manifest.
