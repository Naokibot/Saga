# Saga 0.43.0 validation

Validation is split between executed software, HIL/loopback and unexecuted external/physical dependencies.

Completed before final source binding:
- 0.43 fine-control tests: 7/7 PASS.
- Drone/vision/machine selected regression: 65/65 PASS.
- Language core: 84/84 PASS.
- Modules/generics: 22/22 PASS.
- Ecosystem: 15/15 PASS.
- Native Runtime + Aggregate GC: 24/24 PASS.
- Native Codegen + Native Object: 13/13 PASS.
- Security/runtime selection: 18/18 PASS.
- Go full tests and `go vet`: PASS.
- Python Standard Core self-conformance: 48/48 PASS.
- Go Standard Core self-conformance: 48/48 PASS.

0.43 execution evidence includes a real GStreamer C-API VP8/RTP pipeline, actual RTP bytes received by an OS UDP socket, `webrtcbin` factory loading, a Modbus TCP PLC loopback, CANopen/CiA-402 framing across an OS socketpair, and a 20,000-cycle six-axis servo/PLC HIL plant.

Official PX4/ArduPilot SITL processes, pretrained OpenCV Zoo YOLOX, a physical camera, physical aircraft, and physical servo/PLC/fieldbus hardware remain `UNEXECUTED` in the current container. They are not counted as PASS.
