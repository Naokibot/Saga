# Saga 0.28.0 reviewer handoff

This review should focus on the new `machine` hosted profile and on whether it preserves Saga's existing safety and portability boundaries.

## Suggested review order

1. Verify the frozen tree with `python tools/review_evidence.py --verify release/source-manifest-0.28.0.json`.
2. Read `docs/MACHINE_CONTROL.md` and `RELEASE_NOTES_0.28.0.md` before reading the adapters.
3. Review `saga/stdlib/machine_control.py`, then `saga/stdlib/modules.py` for the Python reference boundary.
4. Review `implementations/go/cmd/saga-go/machine_control.go` and the OS-specific hardware adapter files.
5. Check the `--allow-device` propagation and deterministic resource-close paths in the Go runtime/checker.
6. Run `python -m pytest -q tests/test_machine_control_028.py`.
7. Run `go test ./cmd/saga-go -run TestMachine -count=1` and the race qualification.
8. Run `python tools/machine_control_qualification.py` and confirm that physical hardware remains `UNEXECUTED` unless a real lab supplied it.
9. Run the normal language, Registry, security, Web/Game and SH-3 regressions before approving the release.

## Questions worth challenging

- Can a hardware call occur without device capability, including through an imported Saga module?
- Does a safety trip request zero output immediately rather than only blocking a future write?
- Can `clear()` race with a trip or can watchdog state race between threads?
- Are time values monotonic and implementation-consistent?
- Can a closed handle be reused, panic the runtime, or leave PWM active?
- Do I²C repeated-START, 10-bit addresses, CAN extended IDs and CAN FD/classic receive paths match their Linux wire contracts?
- Can IIO escape `/sys/bus/iio/devices` through path aliases or symlinks?
- Are Python and Go public numeric results stable enough for the same Saga program to compare equal?
- Does any document or validator accidentally turn software/mocked evidence into a physical-machine PASS?

## Safety boundary

The reviewer should reject any wording that implies hard-real-time scheduling or functional-safety certification. Saga 0.28.0 is a software control/supervision layer. Independent machine-safety hardware remains outside the claim.
