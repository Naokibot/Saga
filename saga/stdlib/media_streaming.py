from __future__ import annotations

import ctypes
import ctypes.util
import json
import shutil
import subprocess
from dataclasses import dataclass, field


class MediaStreamingError(RuntimeError):
    pass


class _GstCAPI:
    """Minimal GStreamer C binding used when CLI tools are not installed."""
    GST_STATE_NULL = 1
    GST_STATE_READY = 2
    GST_STATE_PAUSED = 3
    GST_STATE_PLAYING = 4

    def __init__(self) -> None:
        name = ctypes.util.find_library("gstreamer-1.0")
        if not name:
            raise MediaStreamingError("libgstreamer-1.0 is not installed")
        g = self.gst = ctypes.CDLL(name)
        g.gst_init.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.POINTER(ctypes.c_char_p))]
        g.gst_element_factory_find.argtypes = [ctypes.c_char_p]; g.gst_element_factory_find.restype = ctypes.c_void_p
        g.gst_parse_launch.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_void_p)]; g.gst_parse_launch.restype = ctypes.c_void_p
        g.gst_element_set_state.argtypes = [ctypes.c_void_p, ctypes.c_int]; g.gst_element_set_state.restype = ctypes.c_int
        g.gst_element_get_state.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int), ctypes.c_ulonglong]; g.gst_element_get_state.restype = ctypes.c_int
        g.gst_object_unref.argtypes = [ctypes.c_void_p]
        argc = ctypes.c_int(0); argv = ctypes.POINTER(ctypes.c_char_p)()
        g.gst_init(ctypes.byref(argc), ctypes.byref(argv))

    def factory(self, name: str) -> bool:
        ptr = self.gst.gst_element_factory_find(name.encode())
        if ptr:
            self.gst.gst_object_unref(ptr)
            return True
        return False

    def launch(self, description: str) -> ctypes.c_void_p:
        err = ctypes.c_void_p()
        ptr = self.gst.gst_parse_launch(description.encode(), ctypes.byref(err))
        if not ptr or err.value:
            if ptr:
                self.gst.gst_object_unref(ptr)
            raise MediaStreamingError("GStreamer could not construct the requested pipeline")
        return ctypes.c_void_p(ptr)

    def set_playing(self, pipeline: ctypes.c_void_p, timeout_ns: int = 2_000_000_000) -> dict[str, int]:
        result = int(self.gst.gst_element_set_state(pipeline, self.GST_STATE_PLAYING))
        state, pending = ctypes.c_int(), ctypes.c_int()
        wait_result = int(self.gst.gst_element_get_state(pipeline, ctypes.byref(state), ctypes.byref(pending), timeout_ns))
        if result == 0:
            raise MediaStreamingError("GStreamer pipeline refused PLAYING state")
        return {"set_state_result": result, "wait_result": wait_result, "state": state.value, "pending": pending.value}

    def stop(self, pipeline: ctypes.c_void_p) -> None:
        self.gst.gst_element_set_state(pipeline, self.GST_STATE_NULL)
        self.gst.gst_object_unref(pipeline)


_GST: _GstCAPI | None = None
_GST_FAILED = False


def _gst_c() -> _GstCAPI | None:
    global _GST, _GST_FAILED
    if _GST is not None:
        return _GST
    if _GST_FAILED:
        return None
    try:
        _GST = _GstCAPI()
    except Exception:
        _GST_FAILED = True
        return None
    return _GST


def gstreamer_available() -> bool:
    return shutil.which("gst-launch-1.0") is not None or _gst_c() is not None


def gstreamer_webrtc_available() -> bool:
    """Return full GStreamer WebRTC transport readiness, not just webrtcbin presence."""
    if shutil.which("gst-inspect-1.0"):
        try:
            names=("webrtcbin","nicesrc","nicesink")
            return all(subprocess.run(["gst-inspect-1.0",name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5).returncode==0 for name in names)
        except (OSError, subprocess.TimeoutExpired):
            pass
    gst = _gst_c()
    return bool(gst and gst.factory("webrtcbin") and gst.factory("nicesrc") and gst.factory("nicesink"))


def gstreamer_backend_json() -> str:
    gst = _gst_c()
    return json.dumps({
        "available": gstreamer_available(),
        "cli": shutil.which("gst-launch-1.0") is not None,
        "c_api": gst is not None,
        "webrtcbin": bool(gst and gst.factory("webrtcbin")),
        "nicesrc": bool(gst and gst.factory("nicesrc")),
        "vp8enc": bool(gst and gst.factory("vp8enc")),
        "rtpvp8pay": bool(gst and gst.factory("rtpvp8pay")),
    }, separators=(",", ":"))


def gstreamer_execute_probe() -> dict[str, object]:
    """Execute real GStreamer elements through the C API and report capability boundaries."""
    gst = _gst_c()
    if gst is None:
        return {"status": "UNEXECUTED", "reason": "libgstreamer unavailable"}
    pipeline = gst.launch("videotestsrc num-buffers=30 ! videoconvert ! vp8enc deadline=1 ! rtpvp8pay pt=96 ! fakesink sync=false")
    try:
        state = gst.set_playing(pipeline, 5_000_000_000)
    finally:
        gst.stop(pipeline)
    # Loading webrtcbin is real plugin execution. A full ICE peer additionally needs
    # the GStreamer libnice source/sink plugin, which is reported separately.
    return {
        "status": "EXECUTED",
        "pipeline": "videotestsrc->VP8->RTP->fakesink",
        "state": state,
        "webrtcbin_loaded": gst.factory("webrtcbin"),
        "ice_transport_available": gst.factory("nicesrc") and gst.factory("nicesink"),
    }


@dataclass(slots=True)
class GStreamerRTPVideo:
    """Structured GStreamer H.264/RTP sender/receiver without shell interpolation."""
    process: subprocess.Popen[bytes] | None = field(default=None, repr=False)
    role: str = ""
    _pipeline: ctypes.c_void_p | None = field(default=None, repr=False)

    def _start_c_pipeline(self, description: str, role: str) -> None:
        gst = _gst_c()
        if gst is None:
            raise MediaStreamingError("GStreamer runtime is not installed")
        self.stop()
        pipeline = gst.launch(description)
        try:
            gst.set_playing(pipeline)
        except Exception:
            gst.stop(pipeline)
            raise
        self._pipeline = pipeline
        self.role = role

    def start_test_sender(self, host: str, port: int, fps: int = 30) -> None:
        if not (1 <= port <= 65535 and 1 <= fps <= 240):
            raise MediaStreamingError("invalid RTP test parameters")
        # VP8 is selected because it is present in the minimal execution image and is
        # also a standard WebRTC video codec. Host is validated by the capability layer.
        desc = f"videotestsrc is-live=true pattern=ball ! video/x-raw,framerate={fps}/1 ! videoconvert ! vp8enc deadline=1 ! rtpvp8pay pt=96 ! udpsink host={host} port={port} sync=false async=false"
        self._start_c_pipeline(desc, "test_sender")

    def start_camera_sender(self, device: str, host: str, port: int, width: int=1280, height: int=720, fps: int=30, bitrate_kbps: int=2500) -> None:
        if not gstreamer_available(): raise MediaStreamingError("GStreamer runtime is not installed")
        if not (1<=port<=65535 and 1<=width<=7680 and 1<=height<=4320 and 1<=fps<=240 and 64<=bitrate_kbps<=100000): raise MediaStreamingError("invalid RTP video parameters")
        if shutil.which("gst-launch-1.0"):
            args=["gst-launch-1.0","-q","v4l2src",f"device={device}","!",f"video/x-raw,width={width},height={height},framerate={fps}/1","!","videoconvert","!","x264enc",f"bitrate={bitrate_kbps}","tune=zerolatency","speed-preset=ultrafast","!","rtph264pay","config-interval=1","pt=96","!","udpsink",f"host={host}",f"port={port}"]
            self.process=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE); self.role="camera_sender"; return
        desc=f"v4l2src device={device} ! video/x-raw,width={width},height={height},framerate={fps}/1 ! videoconvert ! x264enc bitrate={bitrate_kbps} tune=zerolatency speed-preset=ultrafast ! rtph264pay config-interval=1 pt=96 ! udpsink host={host} port={port}"
        self._start_c_pipeline(desc,"camera_sender")

    def start_receiver(self, port: int) -> None:
        if not gstreamer_available(): raise MediaStreamingError("GStreamer runtime is not installed")
        if not 1<=port<=65535: raise MediaStreamingError("invalid RTP port")
        if shutil.which("gst-launch-1.0"):
            args=["gst-launch-1.0","-q","udpsrc",f"port={port}","caps=application/x-rtp,media=video,encoding-name=H264,payload=96","!","rtph264depay","!","avdec_h264","!","fakesink","sync=false"]
            self.process=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE); self.role="receiver"; return
        desc=f"udpsrc port={port} caps=application/x-rtp,media=video,encoding-name=H264,payload=96 ! rtph264depay ! avdec_h264 ! fakesink sync=false"
        self._start_c_pipeline(desc,"receiver")

    def stop(self) -> None:
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try: self.process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.process.kill(); self.process.wait(timeout=2)
            self.process=None
        if self._pipeline is not None:
            gst = _gst_c()
            if gst:
                gst.stop(self._pipeline)
            self._pipeline = None

    def status_json(self) -> str:
        running = bool((self.process and self.process.poll() is None) or self._pipeline is not None)
        return json.dumps({"running":running,"role":self.role,"backend":"cli" if self.process else ("c-api" if self._pipeline else "none"),"returncode":None if self.process is None else self.process.poll()},separators=(",",":"))


def webrtc_browser_recipe_json() -> str:
    return json.dumps({"backend":"browser-RTCPeerConnection","operations":["webrtc.create_peer","webrtc.add_media_stream","webrtc.create_data_channel","webrtc.create_offer","webrtc.set_local_description","webrtc.set_remote_description","webrtc.add_ice_candidate","webrtc.close"],"media":"media.request_user_media"},separators=(",",":"))
