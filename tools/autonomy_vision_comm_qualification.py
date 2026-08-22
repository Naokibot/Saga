from __future__ import annotations

import argparse
import json
import socket
import sys
import tempfile
from decimal import Decimal as D
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saga.stdlib.drone_control import (
    ControlAllocator,
    LinkMonitor,
    Trajectory3D,
    mavlink_common_decode,
    mavlink_set_attitude_target,
)
from saga.stdlib.vision_control import (
    CentroidTracker,
    Detection,
    PinholeCamera,
    aruco_detect_bgr,
    non_max_suppression,
)

RELEASE = "0.43.0"


def qualify() -> dict[str, object]:
    cases: list[dict[str, object]] = []

    def mark(name: str, passed: bool, detail: object = "") -> None:
        cases.append({"name": name, "pass": bool(passed), "detail": detail})

    # Flight-control primitives: bounded jerk-limited trajectory.
    traj = Trajectory3D.create([D(0), D(0), D(0)], [D(8), D(-3), D(2)], D(3), D(2), D(8))
    max_v = D(0); max_a = D(0); final = None
    for _ in range(1000):
        final = traj.step(D("0.02"))
        max_v = max(max_v, *(abs(v) for v in final["velocity"]))
        max_a = max(max_a, *(abs(a) for a in final["acceleration"]))
        if traj.done():
            break
    mark("3D jerk-limited trajectory reaches target", traj.done() and final is not None and tuple(final["position"]) == (D(8), D(-3), D(2)), {"max_velocity": str(max_v), "max_acceleration": str(max_a)})
    mark("trajectory respects configured limits", max_v <= D(3) and max_a <= D(2))

    # General allocator: six-motor craft with one explicitly disabled actuator.
    s = D("0.8660254037844386")
    matrix = (
        (D(1), D(1), D(0), D(1)), (D(1), D(".5"), s, D(-1)),
        (D(1), D("-.5"), s, D(1)), (D(1), D(-1), D(0), D(-1)),
        (D(1), D("-.5"), -s, D(1)), (D(1), D(".5"), -s, D(-1)),
    )
    allocator = ControlAllocator(matrix, D(0), D(1)); allocator.set_disabled([2])
    allocation_demand=[D(".55"), D(".02"), D("-.01"), D(".01")]
    outputs = allocator.allocate(allocation_demand)
    allocation_report=allocator.allocation_report(allocation_demand)
    mark("general control allocation handles explicit actuator disable", len(outputs) == 6 and outputs[2] == D(0) and all(D(0) <= v <= D(1) for v in outputs), [str(v) for v in outputs])
    mark("control allocation reports achieved demand and residual", allocation_report["commands"] == outputs and allocation_report["disabled"] == [2] and len(allocation_report["residual"]) == 4, allocation_report)

    # Communication observation only: no automatic flight-policy action.
    link = LinkMonitor(alpha=D(".5"))
    for seq, latency in [(10, 10), (11, 12), (14, 20), (14, 30), (13, 40)]:
        link.observe(seq, D(latency))
    stats = link.stats()
    mark("MAVLink sequence/loss/latency monitoring", stats["lost"] == 2 and stats["duplicates"] == 1 and stats["out_of_order"] == 1, stats)

    # Real localhost UDP path carrying a real MAVLink 2 offboard setpoint frame.
    frame = mavlink_set_attitude_target(7, 245, 190, 1, 1, 7, [D(1), D(0), D(0), D(0)], [D(0), D(0), D(0)], D(".45"), 1234)
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); tx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        rx.bind(("127.0.0.1", 0)); rx.settimeout(1.0)
        tx.sendto(frame, rx.getsockname()); data, _ = rx.recvfrom(4096)
        decoded = mavlink_common_decode(data)
        mark("real UDP transport carries SET_ATTITUDE_TARGET", decoded.get("message_id") == 82 and len(data) == len(frame), {"bytes": len(data), "message_id": decoded.get("message_id")})
    finally:
        rx.close(); tx.close()

    # Vision algorithms.
    detections = [
        Detection(1, D(".9"), D(0), D(0), D(100), D(100), "target"),
        Detection(1, D(".8"), D(10), D(10), D(95), D(95), "target"),
        Detection(2, D(".7"), D(10), D(10), D(95), D(95), "other"),
    ]
    kept = non_max_suppression(detections, D(".5"))
    tracker = CentroidTracker(D(30), 2); first = tracker.update([detections[0]])[0]
    second = tracker.update([Detection(1, D(".95"), D(3), D(4), D(103), D(104), "target")])[0]
    camera = PinholeCamera(D(500), D(500), D(320), D(240))
    mark("vision NMS/tracking/camera geometry", len(kept) == 2 and first["track_id"] == second["track_id"] and camera.pixel_to_bearing(D(320), D(240)) == (D(0), D(0), D(1)))

    # Real OpenCV ArUco recognition with generated pixels.
    try:
        import cv2
        import numpy as np
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        marker = cv2.aruco.generateImageMarker(dictionary, 7, 180)
        canvas = np.full((260, 260), 255, np.uint8); canvas[40:220, 40:220] = marker
        bgr = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)
        found = aruco_detect_bgr(bgr, 0)
        mark("real OpenCV ArUco recognition", [x["id"] for x in found] == [7], found)
    except Exception as exc:
        mark("real OpenCV ArUco recognition", False, repr(exc))

    # Real video encode/decode path. This is not a physical camera qualification.
    try:
        import cv2
        import numpy as np
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "vision.avi"
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 5.0, (64, 48))
            if not writer.isOpened():
                raise RuntimeError("OpenCV MJPG writer unavailable")
            writer.write(np.full((48, 64, 3), (0, 128, 255), np.uint8)); writer.release()
            cap = cv2.VideoCapture(str(path)); ok, image = cap.read(); cap.release()
            mark("real OpenCV video frame decode", bool(ok and image is not None and image.shape[:2] == (48, 64)), None if image is None else list(image.shape))
    except Exception as exc:
        mark("real OpenCV video frame decode", False, repr(exc))

    # The learned-model adapter must expose bounded tensor values, not only shapes.
    try:
        import numpy as np
        from PIL import Image
        from saga.stdlib.modules import vision_onnx_forward_json
        class _FakeModel:
            def infer(self, _image):
                return [np.arange(6, dtype=np.float32).reshape(1,2,3), np.arange(6,12,dtype=np.float32).reshape(1,2,3)]
        encoded = json.loads(vision_onnx_forward_json(None, [_FakeModel(), Image.new("RGB", (4, 4)), 8]))
        mark("bounded ONNX tensor output adapter", sum(len(x["values"]) for x in encoded) == 8 and len(encoded[1]["values"]) == 2 and encoded[1]["truncated"] is True, encoded)
    except Exception as exc:
        mark("bounded ONNX tensor output adapter", False, repr(exc))

    # Saga UDP receive can preserve the peer endpoint for multi-vehicle links.
    try:
        from saga.stdlib.modules import net_udp_receive_from_json
        r = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); t = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            r.bind(("127.0.0.1", 0)); r.settimeout(1.0); t.sendto(b"peer", r.getsockname())
            peer = json.loads(net_udp_receive_from_json(None, [r, 32]))
            mark("UDP peer-aware receive metadata", peer["host"] == "127.0.0.1" and peer["data_hex"] == "70656572" and int(peer["port"]) > 0, peer)
        finally:
            r.close(); t.close()
    except Exception as exc:
        mark("UDP peer-aware receive metadata", False, repr(exc))

    # ONNX adapter/backend availability: do not fake a model inference result.
    try:
        import cv2
        dnn_available = hasattr(cv2, "dnn") and hasattr(cv2.dnn, "readNetFromONNX")
        mark("OpenCV DNN ONNX backend API available", dnn_available, getattr(cv2, "__version__", "unknown"))
    except Exception as exc:
        mark("OpenCV DNN ONNX backend API available", False, repr(exc))

    unexecuted = [
        {"name": "physical camera capture", "status": "UNEXECUTED", "reason": "no physical camera is attached to this qualification environment"},
        {"name": "arbitrary ONNX model inference", "status": "UNEXECUTED", "reason": "no reviewed ONNX model artifact is bundled; backend API is checked but model-specific operator coverage is not claimed"},
        {"name": "physical aircraft flight", "status": "UNEXECUTED", "reason": "no aircraft/autopilot/ESC/propeller hardware is attached"},
    ]
    passed = all(bool(c["pass"]) for c in cases)
    return {"schema": 1, "release": RELEASE, "cases": cases, "case_count": len(cases), "unexecuted": unexecuted, "pass": passed}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(ROOT / "validation" / "autonomy-vision-comm-0.43.0.json"))
    args = ap.parse_args()
    report = qualify(); out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps({"release": RELEASE, "cases": report["case_count"], "pass": report["pass"], "unexecuted": len(report["unexecuted"])}, indent=2))
    return 0 if report["pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
