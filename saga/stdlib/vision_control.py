from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Iterable


class VisionError(RuntimeError):
    pass


def _finite(name: str, value: Decimal) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise VisionError(f"{name} must be a finite decimal")
    return value


def _positive(name: str, value: Decimal) -> Decimal:
    value = _finite(name, value)
    if value <= 0:
        raise VisionError(f"{name} must be > 0")
    return value


@dataclass(frozen=True, slots=True)
class Detection:
    class_id: int
    confidence: Decimal
    x1: Decimal
    y1: Decimal
    x2: Decimal
    y2: Decimal
    label: str = ""

    def __post_init__(self) -> None:
        _finite("confidence", self.confidence)
        for name in ("x1", "y1", "x2", "y2"):
            _finite(name, getattr(self, name))
        if not Decimal(0) <= self.confidence <= Decimal(1):
            raise VisionError("confidence must be in 0..1")
        if self.x2 < self.x1 or self.y2 < self.y1:
            raise VisionError("detection box must have x2>=x1 and y2>=y1")

    def iou(self, other: "Detection") -> Decimal:
        ix1, iy1 = max(self.x1, other.x1), max(self.y1, other.y1)
        ix2, iy2 = min(self.x2, other.x2), min(self.y2, other.y2)
        iw, ih = max(Decimal(0), ix2-ix1), max(Decimal(0), iy2-iy1)
        inter = iw*ih
        area_a = max(Decimal(0), self.x2-self.x1) * max(Decimal(0), self.y2-self.y1)
        area_b = max(Decimal(0), other.x2-other.x1) * max(Decimal(0), other.y2-other.y1)
        union = area_a + area_b - inter
        return Decimal(0) if union <= 0 else inter/union

    def center(self) -> tuple[Decimal, Decimal]:
        return (self.x1+self.x2)/2, (self.y1+self.y2)/2


def non_max_suppression(detections: Iterable[Detection], iou_threshold: Decimal) -> list[Detection]:
    threshold = _finite("iou_threshold", iou_threshold)
    if not Decimal(0) <= threshold <= Decimal(1):
        raise VisionError("iou_threshold must be in 0..1")
    pending = sorted(detections, key=lambda d: d.confidence, reverse=True)
    kept: list[Detection] = []
    while pending:
        best = pending.pop(0)
        kept.append(best)
        pending = [d for d in pending if d.class_id != best.class_id or best.iou(d) <= threshold]
    return kept


@dataclass(slots=True)
class CentroidTracker:
    max_distance_px: Decimal
    max_missed_frames: int = 5
    next_id: int = 1
    tracks: dict[int, tuple[Decimal, Decimal, int, int]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.max_distance_px = _positive("max_distance_px", self.max_distance_px)
        if self.max_missed_frames < 0:
            raise VisionError("max_missed_frames must be >= 0")

    def update(self, detections: Iterable[Detection]) -> list[dict[str, object]]:
        dets = list(detections)
        centers = [d.center() for d in dets]
        unmatched_tracks = set(self.tracks)
        unmatched_dets = set(range(len(dets)))
        assignments: list[tuple[int, int]] = []
        candidates: list[tuple[Decimal, int, int]] = []
        for tid, (tx, ty, _, _) in self.tracks.items():
            for di, (dx, dy) in enumerate(centers):
                distance = Decimal(str(math.hypot(float(dx-tx), float(dy-ty))))
                if distance <= self.max_distance_px:
                    candidates.append((distance, tid, di))
        for _, tid, di in sorted(candidates):
            if tid in unmatched_tracks and di in unmatched_dets:
                assignments.append((tid, di)); unmatched_tracks.remove(tid); unmatched_dets.remove(di)
        for tid, di in assignments:
            cx, cy = centers[di]
            _, _, age, _ = self.tracks[tid]
            self.tracks[tid] = (cx, cy, age+1, 0)
        for tid in list(unmatched_tracks):
            cx, cy, age, missed = self.tracks[tid]
            missed += 1
            if missed > self.max_missed_frames:
                del self.tracks[tid]
            else:
                self.tracks[tid] = (cx, cy, age, missed)
        for di in sorted(unmatched_dets):
            cx, cy = centers[di]
            tid = self.next_id; self.next_id += 1
            self.tracks[tid] = (cx, cy, 1, 0)
            assignments.append((tid, di))
        out = []
        for tid, di in sorted(assignments):
            d = dets[di]
            cx, cy, age, missed = self.tracks[tid]
            out.append({"track_id": tid, "class_id": d.class_id, "label": d.label,
                        "confidence": str(d.confidence), "center_x": str(cx), "center_y": str(cy),
                        "age": age, "missed": missed,
                        "box": [str(d.x1), str(d.y1), str(d.x2), str(d.y2)]})
        return out


@dataclass(frozen=True, slots=True)
class PinholeCamera:
    fx: Decimal
    fy: Decimal
    cx: Decimal
    cy: Decimal

    def __post_init__(self) -> None:
        _positive("fx", self.fx); _positive("fy", self.fy)
        _finite("cx", self.cx); _finite("cy", self.cy)

    def pixel_to_bearing(self, u: Decimal, v: Decimal) -> tuple[Decimal, Decimal, Decimal]:
        u, v = _finite("u", u), _finite("v", v)
        x = (u-self.cx)/self.fx
        y = (v-self.cy)/self.fy
        norm = Decimal(str(math.sqrt(float(x*x+y*y+1))))
        return x/norm, y/norm, Decimal(1)/norm


def aruco_detect_bgr(image_bgr: object, dictionary_id: int = 0) -> list[dict[str, object]]:
    """Detect ArUco fiducials in an OpenCV BGR image.

    This provides a deterministic visual-localization primitive for landing pads,
    inspection targets and HIL. It intentionally does not pretend to be a generic
    learned object detector.
    """
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise VisionError("ArUco detection requires OpenCV and NumPy") from exc
    if not isinstance(image_bgr, np.ndarray) or image_bgr.ndim not in (2, 3):
        raise VisionError("aruco_detect_bgr requires an OpenCV/NumPy image")
    dictionaries = [
        cv2.aruco.DICT_4X4_50, cv2.aruco.DICT_4X4_100, cv2.aruco.DICT_5X5_50,
        cv2.aruco.DICT_6X6_50, cv2.aruco.DICT_7X7_50,
    ]
    if not 0 <= int(dictionary_id) < len(dictionaries):
        raise VisionError("dictionary_id must be 0..4")
    dictionary = cv2.aruco.getPredefinedDictionary(dictionaries[int(dictionary_id)])
    detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
    corners, ids, _ = detector.detectMarkers(image_bgr)
    if ids is None:
        return []
    out = []
    for marker_id, pts in zip(ids.flatten().tolist(), corners):
        p = pts.reshape(-1, 2)
        cx, cy = p[:, 0].mean(), p[:, 1].mean()
        out.append({"id": int(marker_id), "center_x": float(cx), "center_y": float(cy),
                    "corners": [[float(x), float(y)] for x, y in p.tolist()]})
    return out


def sparse_optical_flow_velocity_bgr(prev_bgr: object, curr_bgr: object, fx: object, fy: object,
                                     depth_m: object, dt_s: object, max_corners: int = 200) -> dict[str, object]:
    """Estimate camera-plane translation velocity from sparse Lucas-Kanade flow.

    This is a hosted visual front-end for VIO experiments.  Depth/scale is explicit;
    the function does not invent monocular metric scale.  Returned camera convention
    is +x right, +y down and the translation estimate is the negative median image flow.
    """
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise VisionError("optical flow requires OpenCV and NumPy") from exc
    fx = _finite("fx", fx); fy = _finite("fy", fy); depth = _finite("depth_m", depth_m); dt = _finite("dt_s", dt_s)
    if fx <= 0 or fy <= 0 or depth <= 0 or dt <= 0:
        raise VisionError("optical-flow fx/fy/depth/dt must be > 0")
    if not 8 <= int(max_corners) <= 4096:
        raise VisionError("max_corners must be in 8..4096")
    if not isinstance(prev_bgr, np.ndarray) or not isinstance(curr_bgr, np.ndarray):
        raise VisionError("optical flow requires OpenCV/NumPy images")
    if prev_bgr.shape[:2] != curr_bgr.shape[:2]:
        raise VisionError("optical-flow frames must have the same dimensions")
    prev = cv2.cvtColor(prev_bgr, cv2.COLOR_BGR2GRAY) if prev_bgr.ndim == 3 else prev_bgr
    curr = cv2.cvtColor(curr_bgr, cv2.COLOR_BGR2GRAY) if curr_bgr.ndim == 3 else curr_bgr
    pts = cv2.goodFeaturesToTrack(prev, maxCorners=int(max_corners), qualityLevel=0.01, minDistance=5, blockSize=7)
    if pts is None or len(pts) < 4:
        return {"tracked": 0, "median_du": 0.0, "median_dv": 0.0, "camera_velocity_mps": [0.0, 0.0, 0.0]}
    nxt, status, _ = cv2.calcOpticalFlowPyrLK(prev, curr, pts, None, winSize=(21, 21), maxLevel=3,
                                               criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    if nxt is None or status is None:
        return {"tracked": 0, "median_du": 0.0, "median_dv": 0.0, "camera_velocity_mps": [0.0, 0.0, 0.0]}
    good = status.reshape(-1).astype(bool)
    p0 = pts.reshape(-1, 2)[good]; p1 = nxt.reshape(-1, 2)[good]
    if len(p0) < 4:
        return {"tracked": int(len(p0)), "median_du": 0.0, "median_dv": 0.0, "camera_velocity_mps": [0.0, 0.0, 0.0]}
    delta = p1 - p0
    du = float(np.median(delta[:, 0])); dv = float(np.median(delta[:, 1]))
    vx = -du * float(depth) / (float(fx) * float(dt))
    vy = -dv * float(depth) / (float(fy) * float(dt))
    return {"tracked": int(len(p0)), "median_du": du, "median_dv": dv, "camera_velocity_mps": [vx, vy, 0.0]}


def aruco_pose_bgr(image_bgr: object, dictionary_id: int, marker_size_m: object,
                   fx: object, fy: object, cx: object, cy: object) -> list[dict[str, object]]:
    """Estimate 6DoF marker poses using calibrated pinhole intrinsics and solvePnP."""
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise VisionError("ArUco pose requires OpenCV and NumPy") from exc
    size = _finite("marker_size_m", marker_size_m); fx = _finite("fx", fx); fy = _finite("fy", fy); cx = _finite("cx", cx); cy = _finite("cy", cy)
    if size <= 0 or fx <= 0 or fy <= 0:
        raise VisionError("marker size and focal lengths must be > 0")
    detections = aruco_detect_bgr(image_bgr, dictionary_id)
    if not detections:
        return []
    half = float(size) / 2.0
    object_points = np.array([[-half, half, 0.0], [half, half, 0.0], [half, -half, 0.0], [-half, -half, 0.0]], dtype=np.float32)
    camera = np.array([[float(fx), 0.0, float(cx)], [0.0, float(fy), float(cy)], [0.0, 0.0, 1.0]], dtype=np.float64)
    distortion = np.zeros((5, 1), dtype=np.float64)
    out = []
    for detection in detections:
        image_points = np.asarray(detection["corners"], dtype=np.float32)
        ok, rvec, tvec = cv2.solvePnP(object_points, image_points, camera, distortion, flags=cv2.SOLVEPNP_IPPE_SQUARE)
        if not ok:
            continue
        out.append({"id": detection["id"], "rvec": [float(x) for x in rvec.reshape(3)], "tvec_m": [float(x) for x in tvec.reshape(3)]})
    return out


@dataclass(slots=True)
class OpenCVDNNModel:
    path: Path
    input_width: int
    input_height: int
    scale: float = 1.0/255.0
    swap_rb: bool = True
    _net: object = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if self.input_width <= 0 or self.input_height <= 0:
            raise VisionError("DNN input dimensions must be > 0")
        try:
            import cv2
            self._net = cv2.dnn.readNetFromONNX(str(self.path))
        except Exception as exc:
            raise VisionError(f"cannot load ONNX model with OpenCV DNN: {exc}") from exc

    def infer(self, image_bgr: object) -> list[object]:
        try:
            import cv2
            blob = cv2.dnn.blobFromImage(image_bgr, self.scale, (self.input_width, self.input_height), swapRB=self.swap_rb, crop=False)
            self._net.setInput(blob)
            outputs = self._net.forward(self._net.getUnconnectedOutLayersNames())
            if isinstance(outputs, (tuple, list)):
                return list(outputs)
            return [outputs]
        except Exception as exc:
            raise VisionError(f"OpenCV DNN inference failed: {exc}") from exc


def detections_json(detections: Iterable[Detection]) -> str:
    return json.dumps([{"class_id": d.class_id, "label": d.label, "confidence": str(d.confidence),
                        "box": [str(d.x1), str(d.y1), str(d.x2), str(d.y2)]} for d in detections], separators=(",", ":"))

@dataclass(slots=True)
class OpenCVYOLOXDetector:
    """OpenCV-DNN YOLOX object detector compatible with the OpenCV Zoo model.

    The model is a real ONNX network. This wrapper owns preprocessing, anchor/grid
    decoding, score computation and class-aware NMS so Saga code does not need a
    Python post-processing script.
    """
    path: Path
    confidence: Decimal = Decimal("0.35")
    nms_threshold: Decimal = Decimal("0.5")
    input_width: int = 640
    input_height: int = 640
    _net: object = field(init=False, repr=False)
    _grids: object = field(init=False, repr=False)
    _strides: object = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.confidence = _finite("confidence", self.confidence)
        self.nms_threshold = _finite("nms_threshold", self.nms_threshold)
        if not Decimal(0) <= self.confidence <= Decimal(1) or not Decimal(0) <= self.nms_threshold <= Decimal(1):
            raise VisionError("detector thresholds must be in 0..1")
        if self.input_width <= 0 or self.input_height <= 0 or self.input_width % 32 or self.input_height % 32:
            raise VisionError("YOLOX input dimensions must be positive multiples of 32")
        try:
            import cv2
            import numpy as np
            self._net = cv2.dnn.readNet(str(self.path))
            grids=[]; expanded=[]
            for stride in (8,16,32):
                h=self.input_height//stride; w=self.input_width//stride
                xv,yv=np.meshgrid(np.arange(w),np.arange(h))
                grid=np.stack((xv,yv),2).reshape(1,-1,2).astype(np.float32)
                grids.append(grid); expanded.append(np.full((*grid.shape[:2],1),stride,dtype=np.float32))
            self._grids=np.concatenate(grids,1); self._strides=np.concatenate(expanded,1)
        except Exception as exc:
            raise VisionError(f"cannot load YOLOX ONNX model: {exc}") from exc

    @staticmethod
    def _letterbox(image, width: int, height: int):
        import cv2
        import numpy as np
        ih,iw=image.shape[:2]
        ratio=min(width/iw,height/ih)
        nw,nh=max(1,int(iw*ratio)),max(1,int(ih*ratio))
        resized=cv2.resize(image,(nw,nh),interpolation=cv2.INTER_LINEAR).astype(np.float32)
        canvas=np.full((height,width,3),114.0,dtype=np.float32)
        canvas[:nh,:nw]=resized
        return canvas, ratio

    def detect(self, image_bgr: object, labels: list[str] | None = None) -> list[Detection]:
        try:
            import cv2
            import numpy as np
            if not isinstance(image_bgr,np.ndarray) or image_bgr.ndim!=3 or image_bgr.shape[2]!=3:
                raise VisionError("YOLOX detector requires a BGR image")
            rgb=cv2.cvtColor(image_bgr,cv2.COLOR_BGR2RGB)
            padded,ratio=self._letterbox(rgb,self.input_width,self.input_height)
            blob=np.transpose(padded,(2,0,1))[None].astype(np.float32)
            self._net.setInput(blob)
            raw=self._net.forward(self._net.getUnconnectedOutLayersNames())
            out=raw[0] if isinstance(raw,(tuple,list)) else raw
            out=np.asarray(out,dtype=np.float32)
            if out.ndim==2: out=out[None]
            if out.ndim!=3 or out.shape[0]!=1 or out.shape[1]!=self._grids.shape[1] or out.shape[2]<6:
                raise VisionError(f"unexpected YOLOX output shape {tuple(out.shape)}")
            dets=out[0].copy()
            dets[:,:2]=(dets[:,:2]+self._grids[0])*self._strides[0]
            dets[:,2:4]=np.exp(np.clip(dets[:,2:4],-20,20))*self._strides[0]
            obj=dets[:,4:5]; class_scores=dets[:,5:]
            scores=obj*class_scores
            cls=np.argmax(scores,axis=1); conf=np.max(scores,axis=1)
            mask=conf>=float(self.confidence)
            if not np.any(mask): return []
            boxes=dets[mask,:4]; conf=conf[mask]; cls=cls[mask]
            xywh=np.empty_like(boxes)
            xywh[:,0]=boxes[:,0]-boxes[:,2]/2; xywh[:,1]=boxes[:,1]-boxes[:,3]/2
            xywh[:,2]=boxes[:,2]; xywh[:,3]=boxes[:,3]
            keep=cv2.dnn.NMSBoxesBatched(xywh.tolist(),conf.tolist(),cls.astype(int).tolist(),float(self.confidence),float(self.nms_threshold))
            if len(keep)==0: return []
            result=[]
            for idx in np.asarray(keep).reshape(-1).tolist():
                x,y,w,h=[float(v)/ratio for v in xywh[idx]]
                cid=int(cls[idx]); label=labels[cid] if labels and 0<=cid<len(labels) else str(cid)
                result.append(Detection(cid,Decimal(str(float(conf[idx]))),Decimal(str(max(0.0,x))),Decimal(str(max(0.0,y))),Decimal(str(max(0.0,x+w))),Decimal(str(max(0.0,y+h))),label))
            return result
        except VisionError:
            raise
        except Exception as exc:
            raise VisionError(f"YOLOX inference failed: {exc}") from exc

@dataclass(slots=True)
class OpenCVDirectObjectDetector:
    """Generic ONNX detector for models returning rows [x1,y1,x2,y2,score,class_id]."""
    path: Path
    input_width: int
    input_height: int
    confidence: Decimal = Decimal("0.35")
    score_is_logit: bool = False
    _net: object = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.confidence=_finite("confidence",self.confidence)
        if not Decimal(0)<=self.confidence<=Decimal(1): raise VisionError("confidence must be in 0..1")
        if self.input_width<=0 or self.input_height<=0: raise VisionError("detector input dimensions must be >0")
        try:
            import cv2
            self._net=cv2.dnn.readNetFromONNX(str(self.path))
        except Exception as exc: raise VisionError(f"cannot load ONNX detector: {exc}") from exc

    def detect(self,image_bgr: object, labels: list[str] | None=None) -> list[Detection]:
        try:
            import cv2, numpy as np
            blob=cv2.dnn.blobFromImage(image_bgr,1.0/255.0,(self.input_width,self.input_height),swapRB=True,crop=False)
            self._net.setInput(blob); out=np.asarray(self._net.forward(),dtype=np.float32).reshape(-1,6)
            ih,iw=image_bgr.shape[:2]; sx=iw/self.input_width; sy=ih/self.input_height; dets=[]
            for x1,y1,x2,y2,score,cid in out.tolist():
                if self.score_is_logit: score=1.0/(1.0+math.exp(-max(-40.0,min(40.0,score))))
                if score < float(self.confidence): continue
                ci=int(round(cid)); label=labels[ci] if labels and 0<=ci<len(labels) else str(ci)
                dets.append(Detection(ci,Decimal(str(score)),Decimal(str(max(0.0,x1*sx))),Decimal(str(max(0.0,y1*sy))),Decimal(str(max(0.0,x2*sx))),Decimal(str(max(0.0,y2*sy))),label))
            return dets
        except VisionError: raise
        except Exception as exc: raise VisionError(f"ONNX detector inference failed: {exc}") from exc
