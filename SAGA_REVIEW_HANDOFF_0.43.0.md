# Saga 0.43.0 reviewer handoff

Review the release as a hosted general-purpose language with fine-grained drone/machine supervisory control, not as a certified hard-real-time flight controller or safety PLC.

Recommended reproduction order:
1. Verify `release/source-manifest-0.43.0.json`.
2. Run `tests/test_fine_control_043.py`.
3. Run `tools/release_043_qualification.py` and inspect each `status` rather than treating `UNEXECUTED` as PASS.
4. Run Python/Go self-conformance, cross-implementation validation, module conformance and native runtime/codegen qualifications.
5. On a machine with official SITL installed, run `tools/real_sitl_e2e_043.py` against the real PX4 or ArduPilot MAVLink UDP endpoint.
6. Supply the official OpenCV Zoo YOLOX ONNX via a local path and run the `vision.yolox_*` APIs.
7. For physical machine qualification, attach actual drives/PLC/CAN/EtherCAT adapters and preserve independent E-stop/STO.
