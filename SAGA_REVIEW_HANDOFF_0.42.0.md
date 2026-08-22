# Saga 0.42.0 Reviewer Handoff

Start with `RELEASE_NOTES_0.42.0.md`, `docs/AUTONOMY_MACHINE_0.42.md`, `saga-REVIEW_REPORT-0.42.0.md` and `saga-VALIDATION-0.42.0.md`.

High-value independent checks:

1. Run `python tools/review_evidence.py --verify release/source-manifest-0.42.0.json`.
2. Run `python tools/autonomy_stack_qualification_042.py`.
3. Run `python -m unittest tests.test_autonomy_machine_042 tests.test_drone_vision_comm_041 tests.test_drone_control_040`.
4. Run both Saga examples in `examples/drone/visual_vio_slam_swarm.saga` and `examples/machine/advanced_control.saga`.
5. If PX4 or ArduPilot SITL is installed, use `tools/real_sitl_e2e_042.py` against its MAVLink UDP endpoint and retain the JSON output as real-SITL evidence.
6. If GStreamer is installed, inspect the structured RTP pipeline and run sender/receiver with a non-actuating video source before moving to a physical camera.
7. Replace `tests/fixtures/tiny_object_detector.onnx` with a reviewed production model only in a separate model-specific qualification; do not infer model accuracy from the fixture test.

Safety/evidence boundary: no automatic RTL/LAND/DISARM policy has been added. Physical flight, hard-real-time motor stabilization and hazardous machinery qualification require a controlled hardware lab.
