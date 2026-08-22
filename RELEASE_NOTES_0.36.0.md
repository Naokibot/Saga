# Saga 0.36.0 — General-Purpose & Industrial Machine Control Preview

- Adds jerk-limited S-curve motion planning.
- Adds safety-latched supervised axis control with soft limits and following-error trip.
- Adds Modbus RTU master operations with CRC/exception/length validation.
- Adds Modbus TCP master operations with MBAP transaction/protocol/unit/length validation.
- Adds `machine` project template and new machine examples.
- Keeps Native Runtime ABI 0.35; release and ABI versions are now intentionally decoupled when no ABI layout break is required.
- Updates CLI/LSP/package release identity to 0.36.0.

Safety boundary: hosted machine control is soft real-time and does not replace hardwired safety, STO, safety PLCs or MCU/RTOS control where bounded response is required.
