# Saga 0.28.0 release notes

## Theme: advanced machine control without weakening the host safety boundary

Saga 0.28.0 adds the `machine` module as a hosted machine-control profile. The goal is to make one Saga program capable of supervisory robotics and device control while keeping hard-real-time and physical-safety claims explicit.

### Portable control

The module includes PID control with clamping and anti-windup, slew limiting, low-pass filtering, trapezoidal motion profiles, monotonic watchdogs, safety/interlock latches, periodic control-cycle timing, servo pulse mapping, and encoder position/velocity tracking with counter wrap handling.

Portable control functions do not require hardware permission and are available even when the host has no physical machine adapters.

### Linux hardware adapters

Hardware access is gated by `--allow-device` and currently includes:

- I²C through `i2c-dev`, including 7/10-bit addressing and repeated-START combined transfers;
- SPI through `spidev`;
- UART through `termios` with `select`-based timeouts;
- classic CAN and CAN FD through SocketCAN, including extended identifiers;
- Linux PWM sysfs;
- IIO sensor/ADC reads restricted to `/sys/bus/iio/devices`;
- guarded servo output and a two-PWM H-bridge DC motor abstraction.

Binary bus payloads can be expressed portably with `machine.bytes_from_hex` and `machine.bytes_to_hex`.

### Safety and lifecycle

A `SafetyLatch` stops registered motor/servo outputs immediately when tripped. Clearing a latch while a trip is still stopping actuators is rejected, and watchdog state is thread-safe. Hardware resources participate in deterministic cleanup; closed handles fail closed instead of being reused or causing a runtime panic.

This software layer is not a replacement for a hardwired emergency stop, STO, limit/interlock chain, current protection, or a safety-rated controller. The hosted profile is soft real-time. Hard-deadline servo loops belong on an MCU/RTOS or dedicated motion controller.

### Defects found during review

Implementation review caught and fixed repeated-START handling, 10-bit I²C setup, CAN extended-ID encoding, CAN-FD/classic receive compatibility, IIO path containment, device-capability propagation across Saga module boundaries, monotonic-clock inconsistencies, close-after-use crashes, PWM close semantics, servo/motor immediate trip behavior, watchdog and safety-latch races, encoder wrap-around, and public decimal noise at the Python/Go boundary.

### Qualification

`tools/machine_control_qualification.py` performs non-destructive software qualification and records hardware inventory. It never treats missing hardware as physical PASS. `tools/platform_qualification.py` exposes separate `machine-control-software` and `physical-machine-control` gates.

On the current Linux validation host, the software gate passes and physical machine qualification is `UNEXECUTED` because no I²C/SPI/UART/PWM/IIO/CAN devices are exposed.
