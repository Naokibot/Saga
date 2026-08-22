# Saga 0.36.0 Reviewer Handoff

## Release identity

- Release: Saga 0.36.0
- Profile: General-Purpose + Industrial Machine Control Preview
- Native Runtime ABI: 0.35 (intentionally retained)
- Java/hosted machine-control posture: supervised soft real time; fail-closed capabilities

## Fast review path

1. Verify `release/source-manifest-0.36.0.json` with `python tools/review_evidence.py --verify ...`.
2. Run `python -m saga conformance --json`.
3. Run the independent Go implementation conformance and `go test ./...` under `implementations/go`.
4. Run `python tools/cross_implementation_validation.py` and `python tools/module_conformance.py`.
5. Run `python tools/machine_control_qualification.py`.
6. Inspect `docs/MACHINE_CONTROL.md`, `docs/GENERAL_PURPOSE_READINESS_0.36.md`, and `RELEASE_NOTES_0.36.0.md` for scope/claim boundaries.

## Safety-review focus

Pay particular attention to:

- device and network capability gates;
- Modbus response/length/CRC/transaction validation;
- per-transaction timeout refresh;
- axis soft-limit and following-error trip behavior;
- safety-latch behavior after a trip;
- absence of any claim that hosted scheduling provides hard real-time determinism;
- no assumption that software safety replaces external E-stop/interlock hardware.
