# Saga 0.44.0 review — 4 kHz hosted control

## Scope
Saga 0.44 targets 4,000 **logical control-state updates per second** with a 250 us nominal period while preserving the distinction between hosted scheduling and hard-real-time physical I/O.

## Design review
- Linux Python runtime uses periodic `timerfd`, so kernel expiration counts are not silently lost during process pre-emption.
- `cycle_wait_due()` exposes catch-up count instead of hiding missed host execution slots.
- Portable Python fallback uses absolute monotonic deadlines plus a short sleep/spin guard.
- Independent Go runtime provides the same frequency-based cyclic API and due-count semantics with an absolute-deadline sleep/spin scheduler.
- Existing cached control allocation, compact state-space control and per-actuator slew/deadband conditioning fit inside the 250 us compute budget in the qualification environment.
- 4 kHz scheduling does not automatically arm, disarm, land, RTL, stop machinery, or alter safety policy.

## Important boundary
A logical due count of 4,000 in one second does not prove that a physical PWM edge, CAN frame, EtherCAT PDO, or motor-current update occurred on every exact 250 us deadline. Any hazardous or truly hard-real-time path still requires a qualified RTOS/PREEMPT_RT/drive/FPGA/hardware-timer backend, external E-stop/STO/interlocks, and device-specific timing evidence.

## Review findings fixed
1. Sub-millisecond `time.sleep()` was unsuitable as the primary Linux 4 kHz scheduler.
2. Missed periods were previously represented only as lateness/overrun; 0.44 exposes the number of due state updates.
3. Timerfd expirations are treated as authoritative and are not double-counted by user-space lateness logic.
4. Version/API documentation and the independent Go checker/runtime were updated together.
