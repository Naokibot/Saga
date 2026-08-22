# Saga 0.47.0 validation

Saga 0.47 validation separates algorithm/compiler evidence from physical fieldbus, motor, timing and safety claims.

## Completed regression groups before source freeze

- advanced-motion + retained precision/machine control: **50/50 PASS**;
- core language + Natural language + modules + retained 0.45 synthesis: **82/82 PASS**;
- selected Standard language/runtime safety/Native Runtime/Native Codegen: **37/37 PASS**;
- retained drone/vision/autonomy/fine-control/4 kHz group: **44/44 PASS**;
- Go full `go test ./...`: **PASS**;
- Go `go vet ./...`: **PASS**;
- Go Race Detector on the 0.47 advanced-motion + retained 0.46 precision tests: **PASS**.

The 0.47 Python test module covers FOC current control and voltage limiting, encoder unwrap/alignment, RLS convergence, MPC bounded response, disturbance observation, Stribeck symmetry, multi-axis correction/skew, EtherCAT codec, CAN-FD metadata, device-capability denial, common source execution and the allocation-free source profile.

## Source-bound release evidence

The final candidate also contains `tools/advanced_motion_qualification_047.py`, `tools/machine_control_qualification.py`, module/differential/self-conformance tools, a source-manifest verifier, specification lint and project-internal security audit. Their generated JSON evidence lives under `validation/` and is excluded from the source-tree digest so evidence generation does not mutate the reviewed source.

## Physical qualification boundary

The following are intentionally **UNEXECUTED / NOT CLAIMED** by this release:

- physical high-bandwidth FOC against a motor, inverter and current sensors;
- exact ADC/PWM trigger/dead-time timing;
- physical incremental/absolute encoder electrical interfaces;
- CAN-FD BRS operation on a real controller/interface;
- EtherCAT slave discovery, PDO exchange, Distributed Clocks synchronization and conformance;
- NIC hardware timestamp calibration/accuracy;
- MCU/RTOS target WCET and object-code proof of zero allocator calls;
- E-stop, STO, over-current, hard limits or functional-safety certification.

The release can therefore be described as a validated common software/control profile, not as a certified hard-real-time motion controller.
