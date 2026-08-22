# Saga 0.28.0 machine-control review report

## Scope

The review covered the portable control layer, Linux device adapters, Python/Go parity, capability propagation, resource lifecycle, concurrency, public numeric behavior, qualification tooling and regressions outside the machine module.

## Defects corrected during implementation review

The review found and fixed concrete issues rather than treating the first implementation as final:

- Python I²C ctypes declarations originally failed at import because nested structure names were resolved in the wrong class scope.
- Go runtime module dispatch initially recognized `machine` in the checker but not at runtime.
- I²C combined register reads initially performed write/STOP/read rather than an `I2C_RDWR` repeated-START transaction.
- 10-bit I²C addresses were accepted without enabling TENBIT mode/message flags; combined segment sizes could also truncate to 16 bits.
- Go IIO containment used an unsafe path-prefix test; it now resolves the target and validates it relative to `/sys/bus/iio/devices`.
- CAN extended identifiers lacked `CAN_EFF_FLAG`; Python CAN-FD receive assumed every frame had CAN-FD size and failed on classic frames.
- Device permission did not propagate into imported Go Saga modules, while Python `servo_guard` could perform immediate safety I/O without first requiring the device capability.
- Python and Go exposed small floating-point representation differences at the Saga boundary; control results are now normalized to a stable public decimal representation.
- Python/Go monotonic-time helpers used inconsistent time bases in several paths.
- I²C/UART/CAN/PWM use-after-close paths could be inconsistent or, in Go, panic through a nil/invalid handle.
- PWM close behaved like a temporary disable and allowed reuse; close is now final and idempotent.
- Motor/servo safety originally blocked only future writes. Registered actuators now receive an immediate zero-output stop request on trip.
- `SafetyLatch.clear()` could race a trip while stop callbacks were running. A trip-in-progress state now prevents that clear.
- Go watchdog state could race between feed and monitor goroutines; watchdog access is synchronized in both implementations.
- Encoder tracking did not account for hardware counter wrap-around.
- Portable Saga code had no implementation-neutral way to construct arbitrary binary bus payloads; `bytes_from_hex`/`bytes_to_hex` were added.

## Review result

No unresolved defect was found by this project-internal review in the changed machine-control paths after the fixes above. This is not a claim that no defects exist and is not an independent penetration, functional-safety or hardware qualification.

Physical I²C/SPI/UART/CAN/PWM/IIO/motor/servo qualification was not possible on the current host because those devices are not exposed. The software qualification deliberately records that state as `UNEXECUTED`.
