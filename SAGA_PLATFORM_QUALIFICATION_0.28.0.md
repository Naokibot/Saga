# Saga 0.28.0 platform qualification

Saga 0.28.0 adds a hosted machine-control profile without changing the rule that external hardware evidence must be earned on the hardware it names.

## Machine-control gates

`tools/platform_qualification.py` reports two separate gates:

- `machine-control-software`: portable control algorithms, capability checks, adapter contracts and non-destructive examples must pass on the review host.
- `physical-machine-control`: requires an operator-controlled hardware lab. The default qualification never energizes a motor or servo and therefore cannot satisfy this gate.

The current hosted profile is soft real-time. A passing software gate does not assert bounded scheduling latency, machine-safety certification, or correctness of external wiring/power electronics.

## Non-destructive qualification

Run:

```bash
python tools/machine_control_qualification.py
python tools/platform_qualification.py
```

The machine qualification executes the Python and Go control tests, typechecks the machine examples, runs Go vet, checks capability denial paths and records visible hardware inventory. Missing hardware is reported as `UNEXECUTED` rather than PASS.

## Physical lab expectations

A physical qualification should bind its evidence to the release source manifest and record the exact host, adapters, bus devices, wiring fixture and external safety measures. At minimum, a real lab should separately verify:

1. I²C repeated-START and 7/10-bit addressing against a known device.
2. SPI loopback or a known register device at the configured mode/clock.
3. UART loopback with timeout/error handling.
4. classic CAN, CAN FD and extended-ID transmission/readback.
5. PWM period/duty readback with no actuator connected first.
6. IIO/ADC scaling against a known reference signal.
7. encoder direction, wrap-around and velocity sign.
8. motor/servo zero-output behavior on a software safety trip.
9. watchdog and interlock behavior while the control loop is deliberately stalled.
10. independent hardwired emergency-stop/STO/interlock behavior without relying on the Saga process.

The last item is intentionally outside Saga's software safety claim. Systems capable of harm require hardware protection appropriate to their application and jurisdiction.

## Existing external gates

Vulkan physical GPU rendering, Windows/macOS native-host execution, Android/iOS devices, a public HTTPS Registry, live AWS, physical GPIO/gamepads and independent security review remain distinct evidence tracks. Cross-builds, mocks and software-rendered devices do not satisfy a physical gate.
