# Saga 0.44.0 reviewer handoff

Review the source manifest first, then run:

```bash
python tools/review_evidence.py --verify release/source-manifest-0.44.0.json
python tools/control_4khz_qualification_044.py
python -m unittest tests.test_control_4khz_044 tests.test_fine_control_043 tests.test_machine_control_028 tests.test_machine_control_036
cd implementations/go && go test ./... && go vet ./...
```

Key files:
- `saga/stdlib/fine_control.py`
- `saga/stdlib/modules.py`
- `implementations/go/cmd/saga-go/machine_control.go`
- `implementations/go/cmd/saga-go/checker.go`
- `tests/test_control_4khz_044.py`
- `tools/control_4khz_qualification_044.py`
- `docs/CONTROL_4KHZ_0.44.md`

Interpret `cycle_wait_due() > 1` as host scheduling debt. It permits deterministic state catch-up but is **not** evidence that physical outputs met the missed 250 us deadlines.
