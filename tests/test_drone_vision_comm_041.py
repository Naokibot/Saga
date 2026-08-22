import json, math, unittest
from decimal import Decimal as D

from saga.stdlib.drone_control import Trajectory3D, ControlAllocator, LinkMonitor
from saga.stdlib.vision_control import Detection, non_max_suppression, CentroidTracker, PinholeCamera, aruco_detect_bgr
from saga.stdlib.modules import MODULES

class DroneVisionComm041Test(unittest.TestCase):
    def test_trajectory_jerk_limited(self):
        t=Trajectory3D.create([D(0),D(0),D(0)],[D(10),D(-4),D(2)],D(3),D(2),D(8))
        prev=[D(0),D(0),D(0)]
        for _ in range(800):
            state=t.step(D('0.02'))
            self.assertTrue(all(abs(a)<=D(2) for a in state['acceleration']))
            self.assertTrue(all(abs(v)<=D(3) for v in state['velocity']))
            prev=list(state['position'])
            if t.done(): break
        self.assertTrue(t.done()); self.assertEqual(prev,[D(10),D(-4),D(2)])

    def test_hex_allocator_survives_one_disabled_motor(self):
        s=D('0.8660254037844386')
        matrix=((D(1),D(1),D(0),D(1)),(D(1),D('.5'),s,D(-1)),(D(1),D('-.5'),s,D(1)),
                (D(1),D(-1),D(0),D(-1)),(D(1),D('-.5'),-s,D(1)),(D(1),D('.5'),-s,D(-1)))
        a=ControlAllocator(matrix,D(0),D(1)); a.set_disabled([2])
        demand=[D('.5'),D('.02'),D('-.01'),D('.01')]
        out=a.allocate(demand)
        self.assertEqual(len(out),6); self.assertEqual(out[2],D(0)); self.assertTrue(all(D(0)<=v<=D(1) for v in out))
        report=a.allocation_report(demand)
        self.assertEqual(report["commands"],out); self.assertEqual(report["disabled"],[2]); self.assertEqual(len(report["residual"]),4)

    def test_link_monitor(self):
        m=LinkMonitor(alpha=D('.5'))
        for seq,lat in [(10,10),(11,12),(14,20),(14,30),(13,40)]: m.observe(seq,D(lat))
        s=m.stats(); self.assertEqual((s['lost'],s['duplicates'],s['out_of_order']),(2,1,1))

    def test_nms_tracking_and_camera_geometry(self):
        ds=[Detection(1,D('.9'),D(0),D(0),D(100),D(100),'target'),Detection(1,D('.8'),D(10),D(10),D(95),D(95),'target'),Detection(2,D('.7'),D(10),D(10),D(95),D(95),'other')]
        kept=non_max_suppression(ds,D('.5')); self.assertEqual(len(kept),2)
        tr=CentroidTracker(D(30),2); a=tr.update([ds[0]])[0]; b=tr.update([Detection(1,D('.95'),D(3),D(4),D(103),D(104),'target')])[0]
        self.assertEqual(a['track_id'],b['track_id'])
        cam=PinholeCamera(D(500),D(500),D(320),D(240)); bearing=cam.pixel_to_bearing(D(320),D(240))
        self.assertEqual(bearing,(D(0),D(0),D(1)))

    def test_real_opencv_aruco_recognition(self):
        import cv2, numpy as np
        dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        marker=cv2.aruco.generateImageMarker(dictionary, 7, 180)
        canvas=np.full((260,260),255,np.uint8); canvas[40:220,40:220]=marker
        bgr=cv2.cvtColor(canvas,cv2.COLOR_GRAY2BGR)
        found=aruco_detect_bgr(bgr,0)
        self.assertEqual([x['id'] for x in found],[7])


    def test_video_frame_pipeline_uses_real_opencv_decoder(self):
        import cv2, numpy as np, tempfile
        from pathlib import Path
        from saga.stdlib.modules import video_open, video_read_frame, image_width, image_height
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"sample.avi"
            writer=cv2.VideoWriter(str(path),cv2.VideoWriter_fourcc(*"MJPG"),5.0,(64,48))
            self.assertTrue(writer.isOpened())
            writer.write(np.full((48,64,3),(0,0,255),np.uint8)); writer.release()
            # Call through the registered native functions to exercise Saga resource checks.
            fn=MODULES['video'].functions['open']; rf=MODULES['video'].functions['read_frame']
            class Caps:
                def require_read(self,p): return Path(p)
            class I:
                capabilities=Caps()
                def register_resource(self,x): return x
            cap=fn.impl(I(),[str(path)]); image=rf.impl(I(),[cap])
            self.assertEqual((image.width,image.height),(64,48)); cap.release()


    def test_bounded_onnx_output_serialization_and_udp_peer(self):
        import socket, numpy as np
        from PIL import Image
        from saga.stdlib.modules import vision_onnx_forward_json, net_udp_receive_from_json
        class FakeModel:
            def infer(self, _image): return [np.arange(6,dtype=np.float32).reshape(1,2,3),np.arange(6,12,dtype=np.float32).reshape(1,2,3)]
        image=Image.new("RGB",(4,4))
        payload=json.loads(vision_onnx_forward_json(None,[FakeModel(),image,8]))
        self.assertEqual(payload[0]["shape"],[1,2,3]); self.assertEqual(sum(len(x["values"]) for x in payload),8)
        self.assertEqual(len(payload[1]["values"]),2); self.assertTrue(payload[1]["truncated"])
        rx=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); tx=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        try:
            rx.bind(("127.0.0.1",0)); rx.settimeout(1)
            tx.sendto(b"abc",rx.getsockname())
            got=json.loads(net_udp_receive_from_json(None,[rx,16]))
            self.assertEqual(got["data_hex"],"616263"); self.assertEqual(got["host"],"127.0.0.1")
            self.assertGreater(got["port"],0)
        finally:
            rx.close(); tx.close()

    def test_saga_native_modules_expose_new_capabilities(self):
        self.assertIn('vision',MODULES)
        for name in ['trajectory3d','quad_x_allocator','allocation_report_json','link_monitor']:
            self.assertIn(name,MODULES['drone'].functions)
        for name in ['nms_json','tracker','camera','aruco_detect_json','onnx_load','onnx_forward_json']:
            self.assertIn(name,MODULES['vision'].functions)
        self.assertIn('set_timeout_ms',MODULES['net'].functions)
        self.assertIn('udp_receive_from_json',MODULES['net'].functions)
        self.assertIn('open_camera',MODULES['video'].functions)
        self.assertIn('read_frame',MODULES['video'].functions)

if __name__=='__main__': unittest.main()
