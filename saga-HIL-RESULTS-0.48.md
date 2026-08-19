# Saga Advanced Motion Virtual-HIL 0.48 — Qualification Report

## Verdict

**Virtual/software qualification: PASS. Physical hardware qualification: UNEXECUTED.**

This campaign was run because the execution environment has no attached motor/inverter, absolute encoder, CAN-FD controller, EtherCAT ESC network, PTP-capable NIC, safety relay or STO-capable drive. Results below are therefore simulation/kernel/toolchain evidence and must not be represented as physical certification.

Base Saga 0.47 frozen source tree SHA-256: `87a5d5065d969ff173ec53919bea7de6ff07581e7473e036783dfd4e53db4a3a`  
Qualification overlay SHA-256: `97a4c51678d832201af86100723a9d3286ce8d836392c56d4d0544fe2b5f0f94`

## Results

| Area | Result | Evidence |
|---|---|---|
| High-bandwidth FOC | PASS (virtual HIL) | 20 kHz loop, nominal 1 kHz current bandwidth, 100/100 parameter-variation cases passed; nominal 2% settling 1.450 ms, overshoot 2.162%, final q-current error 0.0074 A |
| Absolute encoder | PASS (virtual HIL) | 17-bit, 3000 rpm, 10 kHz, ±1 count noise, ±200 ns timestamp jitter, 202 dropped-sample events; max position error 0.004065°, p99 velocity error 3.348 rpm |
| CAN-FD BRS | PASS (ABI + model) | Saga 72-byte SocketCAN FD frame preserved BRS and 64-byte payload; modeled 64-byte frame 705.6 µs without BRS vs 177.6 µs at 1/5 Mbit/s. Kernel vcan creation: UNAVAILABLE (RTNETLINK answers: Operation not permitted) |
| EtherCAT Distributed Clocks | PASS (register framing + clock model) | DC frames exercised 0x0900, 0x0910, 0x092C; 4-slave model p99 max skew 25.43 ns, worst 29.15 ns after lock |
| NIC timestamps | PASS (provenance + model) | Actual Linux loopback software timestamp path: 200 packets; no `/dev/ptp*`; virtual 8 ns PHC model p99 error 14.23 ns |
| MCU zero allocation | PASS for restricted generated kernel | Cortex-M4F object SHA `c12433f88382fd0d33ea1d3ddbfb7ea5ec431a71d8e1912806f4f47f47946d22`; allocator refs 0, subroutine calls 0, static stack 0 bytes, acyclic instruction upper bound 22 instructions |
| WCET | PARTIAL / model only | Pessimistic virtual envelope 352 cycles = 2.095 µs at 168 MHz. **Formal target WCET is not proven.** |
| STO / E-stop | PASS (fault-injection model) | dual-channel stop 2.0 ms model; restart prevention, channel discrepancy and welded-channel fault cases passed. **No SIL/PL claim.** |

## Regression

- New Virtual-HIL tests: **7/7 PASS**.
- New + retained machine/FOC/precision/4 kHz selection: **59/59 PASS**.
- Go implementation: `go test ./...` **PASS** and `go vet ./...` **PASS**.
- New qualification scripts: Python byte-code compile **PASS**.

## What was physically attempted

- The host exposes Linux `AF_CAN` and `AF_PACKET`, but creating a `vcan` interface failed with `RTNETLINK answers: Operation not permitted`; the sandbox lacks the network-administration capability required for this setup.
- `eth0` is backed by a virtio device and no `/dev/ptp*` hardware clock device is exposed. Therefore NIC hardware timestamp precision could not be measured.
- No physical motion/safety hardware is connected.

## Interpretation

The most important distinction is between **model qualification** and **physical qualification**. The FOC result shows that the current Saga controller remains stable and tracks current under the declared simulated PMSM/inverter disturbances; it does not prove a particular motor/inverter combination. The EtherCAT result verifies DC register traffic can be expressed and that a modeled clock network converges; it does not prove an ESC implementation, cable topology or ETG conformance. The Cortex-M4F object inspection proves allocator absence only for the generated restricted q-axis `@control_tick` kernel, not all Saga programs.

## Reference basis used for the virtual models

- EtherCAT Technology Group Distributed Clocks knowledge base: DC capture registers at 0x0900, system time at 0x0910, offset at 0x0920, delay at 0x0928, and system-time difference at 0x092C.
- Linux kernel timestamping documentation: `SOF_TIMESTAMPING_RX_HARDWARE`, `SOF_TIMESTAMPING_RX_SOFTWARE`, `SOF_TIMESTAMPING_RAW_HARDWARE`, with raw hardware receive timestamps reported in the hardware timestamp slot.
- Arm Cortex-M4 documentation: optional single-precision FPU; actual timing depends on the concrete MCU/memory/interrupt implementation, which is why the report does not promote the virtual cycle envelope to formal WCET.

## Required physical follow-up before production use

1. Motor/inverter dynamometer test with current probes, DC-bus measurement and oscilloscope/logic-analyzer capture of PWM/ADC timing.
2. Absolute encoder test over full speed/temperature range, including power-cycle/multi-turn behavior and communication faults.
3. Real CAN-FD controller/transceiver pair with configured arbitration/data bit timing, BRS, bus errors and timestamp capture.
4. Real EtherCAT DC-capable ESC chain with propagation-delay calibration and measured Sync0/Sync1 skew.
5. PTP-capable NIC/PHC timestamp test against an external time reference.
6. Final MCU binary generated with the production compiler/linker/BSP, allocator-symbol audit, stack proof, interrupt model and WCET measurement/static analysis on the actual target.
7. STO/E-stop validation with the selected safety drive/relay, dual-channel wiring, feedback/EDM, fault injection and the applicable safety lifecycle/certification process.
