# Saga 0.43 fine-grained control

## Machine

`machine.actuator_bank` provides a deliberately policy-free cyclic actuator conditioner. Each channel can be set independently or as a batch. The bank applies only the limits requested by the program: minimum, maximum, neutral/deadband and slew rate. `machine.actuator_zero` is an explicit command, not an automatic safety transition.

`machine.cyclic_clock` is a hosted scheduling helper. It records late wakeups and overruns and reports `hosted-soft-realtime`; it does not claim deterministic deadlines.

`machine.fast_state_space` stores a compact float matrix representation once and converts only API-boundary values. Use the exact Decimal state-space controller when exact arithmetic is more important than cyclic cost.

## Drone

`drone.trajectory3d_limits` accepts independent X/Y/Z maximum velocity, acceleration and jerk arrays. `drone.sitl_attitude`, `drone.sitl_position_batch_json` and `drone.sitl_timeout_ms` expose lower-level offboard choices to the Saga program. No automatic flight-policy layer is introduced.

## Runtime/backend boundary

Saga source can compose the full supported control algorithm. Kernel drivers, physical bus controllers, deterministic Ethernet/CAN scheduling, GPU/camera drivers and timer/DMA waveform generation remain runtime backends. This is the same separation used by general-purpose native languages; it is not a claim that software can replace absent hardware.

## 0.44 4 kHz profile

Saga 0.44 keeps the 0.43 fine-control APIs and replaces sub-millisecond `time.sleep` scheduling on Linux with a kernel `timerfd` periodic source. Use `machine.cycle_wait_due(clock)` when running at 4 kHz so missed host scheduling slots are visible and deterministic state updates can catch up. Physical deadline compliance remains a separate hardware/RTOS qualification question.
