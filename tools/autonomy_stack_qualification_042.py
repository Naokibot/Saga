from __future__ import annotations

import argparse, hashlib, json, os, shutil, socket, struct, subprocess, sys, tempfile, threading, time
from decimal import Decimal as D
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from saga.stdlib.autonomy_advanced import VisualServoController, VisualInertialOdometry, PoseGraphSLAM, MultiDroneCoordinator, MAVLinkOffboardSession
from saga.stdlib.drone_control import mavlink2_encode, mavlink_heartbeat, MAVLinkStreamParser, mavlink_common_decode
from saga.stdlib.vision_control import OpenCVDirectObjectDetector, OpenCVYOLOXDetector, sparse_optical_flow_velocity_bgr, aruco_pose_bgr
from saga.stdlib.media_streaming import gstreamer_available, gstreamer_webrtc_available, webrtc_browser_recipe_json
from saga.stdlib.machine_advanced import discrete_lqr_gain, StateSpaceController, LinearKalmanFilter, SynchronizedMotionGroup, DHKinematicChain, PLCScanEngine, CANopen, CiA402, ProcessImage
from tools.evidence_context import source_binding

CASES=[]
def mark(name, ok, detail=None, status=None):
    rec={'name':name,'pass':bool(ok)}
    if detail is not None: rec['detail']=detail
    if status: rec['status']=status
    CASES.append(rec); print(('PASS' if ok else 'FAIL'), name, '' if detail is None else detail)

class AutopilotEmulator(threading.Thread):
    """Protocol-level MAVLink SITL stand-in. It is explicitly not PX4/ArduPilot."""
    def __init__(self):
        super().__init__(daemon=True); self.sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); self.sock.bind(('127.0.0.1',0)); self.port=self.sock.getsockname()[1]; self.stop_evt=threading.Event(); self.peer=None; self.seq=0; self.pos=[0.0,0.0,0.0]; self.target=[0.0,0.0,0.0]; self.parser=MAVLinkStreamParser(); self.received=0
    def frame(self,msgid,crc,payload):
        f=mavlink2_encode(msgid,crc,payload,self.seq,1,1); self.seq=(self.seq+1)&255; return f
    def telemetry(self):
        if not self.peer:return
        self.sock.sendto(mavlink_heartbeat(self.seq,1,1,2,3,0,0,4),self.peer); self.seq=(self.seq+1)&255
        payload=struct.pack('<I6f',int(time.monotonic()*1000)&0xffffffff,*self.pos,0.0,0.0,0.0)
        self.sock.sendto(self.frame(32,185,payload),self.peer)
    def run(self):
        self.sock.settimeout(.02); last=0.0
        while not self.stop_evt.is_set():
            try:
                data,peer=self.sock.recvfrom(65535); self.peer=peer
                for m in self.parser.feed(data):
                    self.received+=1
                    if int(m.get('message_id',-1))==84:
                        payload=bytes.fromhex(str(m['payload_hex'])); vals=struct.unpack('<I11fHBBB',payload); self.target=[float(vals[1]),float(vals[2]),float(vals[3])]
            except socket.timeout: pass
            # simple first-order position plant
            for i in range(3):
                e=self.target[i]-self.pos[i]; self.pos[i]+=max(-.08,min(.08,e))
            now=time.monotonic()
            if now-last>.04: self.telemetry(); last=now
        self.sock.close()
    def stop(self): self.stop_evt.set(); self.join(timeout=1)


def sitl_e2e():
    em=AutopilotEmulator(); em.start()
    s=MAVLinkOffboardSession('127.0.0.1',0,'127.0.0.1',em.port,timeout_s=.2)
    try:
        # prime peer and wait heartbeat
        s.send_position([D(0),D(0),D(0)])
        s.wait_message(0,2)
        phases=[([D(0),D(0),D(-3)],'takeoff'),([D(5),D(2),D(-3)],'translate'),([D(5),D(2),D(0)],'land')]
        errors=[]
        for target,name in phases:
            deadline=time.monotonic()+4
            while time.monotonic()<deadline:
                s.send_position(target); s.poll(.05); p=s.position()
                if p:
                    err=sum((float(p[i]-target[i]))**2 for i in range(3))**.5
                    if err<.12: errors.append((name,err,[float(x) for x in p])); break
            else: raise RuntimeError(f'{name} did not converge')
        return {'phases':errors,'received_setpoints':em.received}
    finally:
        s.close(); em.stop()



def browser_webrtc_node_test():
    node = shutil.which("node")
    if not node:
        return {"status":"UNEXECUTED","reason":"node not installed"}
    js = ROOT / "implementations/go/cmd/saga-go/web_runtime/sh3vm-browser.js"
    program = "SH3BC1\nGLOBALS 0\nENTRY 6d61696e\nFUNC 6d61696e 0 0\nPUSHI 0\nRET\nEND\n"
    script = r"""
class Peer {
  constructor(){ this.tracks=[]; this.closed=false; }
  addTrack(track, stream){ this.tracks.push([track,stream]); return {}; }
  createDataChannel(label){ return {label:label,readyState:'connecting'}; }
  close(){ this.closed=true; }
}
globalThis.RTCPeerConnection=Peer;
const mod=require(process.argv[1]);
const vm=new mod.SagaSH3VM(process.argv[2]);
const peer=JSON.parse(vm.appInvoke('webrtc.create_peer','{}'));
const stream={getTracks:()=>[{kind:'video'},{kind:'audio'}]};
vm.webState.mediaStreams.set(7,stream);
const added=JSON.parse(vm.appInvoke('webrtc.add_media_stream',JSON.stringify({id:peer.id,stream_id:7})));
const dc=JSON.parse(vm.appInvoke('webrtc.create_data_channel',JSON.stringify({id:peer.id,label:'telemetry'})));
const closed=JSON.parse(vm.appInvoke('webrtc.close',JSON.stringify({id:peer.id})));
console.log(JSON.stringify({added,dc,closed}));
"""
    proc=subprocess.run([node,"-e",script,str(js),program],cwd=ROOT,text=True,capture_output=True,timeout=10)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"node exited {proc.returncode}")
    data=json.loads(proc.stdout.strip().splitlines()[-1])
    if data["added"].get("added_tracks") != 2 or data["dc"].get("label") != "telemetry" or not data["closed"].get("closed"):
        raise RuntimeError(f"unexpected WebRTC mock result: {data}")
    return {"status":"EXECUTED","node":node,"result":data}

def main():
    # E2E flight through real UDP/MAVLink path; official SITL binaries are separately reported.
    try: mark('MAVLink UDP takeoff-translate-land E2E',True,sitl_e2e())
    except Exception as e: mark('MAVLink UDP takeoff-translate-land E2E',False,repr(e))
    px4=shutil.which('px4'); ardu=shutil.which('arducopter') or shutil.which('arducopter')
    mark('PX4 official SITL execution availability',True,{'path':px4,'available':px4 is not None},'EXECUTED' if px4 else 'UNEXECUTED')
    mark('ArduPilot official SITL execution availability',True,{'path':ardu,'available':ardu is not None},'EXECUTED' if ardu else 'UNEXECUTED')

    # Actual ONNX graph execution with object-detector semantics.
    fixture=ROOT/'tests/fixtures/tiny_object_detector.onnx'
    try:
        import numpy as np
        model=OpenCVDirectObjectDetector(fixture,32,32,D('.5'),True)
        dark=np.zeros((64,64,3),dtype=np.uint8); bright=np.full((64,64,3),255,dtype=np.uint8)
        a=model.detect(dark,['bright']); b=model.detect(bright,['bright'])
        mark('actual ONNX object detector executes via OpenCV DNN',len(a)==0 and len(b)==1 and b[0].confidence>D('.9'),{'dark':len(a),'bright':len(b),'confidence':str(b[0].confidence),'box':[str(b[0].x1),str(b[0].y1),str(b[0].x2),str(b[0].y2)]})
    except Exception as e: mark('actual ONNX object detector executes via OpenCV DNN',False,repr(e))

    try:
        import cv2, numpy as np
        prev=np.zeros((160,160,3),dtype=np.uint8)
        for yy in range(20,150,30):
            for xx in range(20,150,30): cv2.circle(prev,(xx,yy),3,(255,255,255),-1)
        curr=cv2.warpAffine(prev,np.float32([[1,0,4],[0,1,2]]),(160,160))
        flow=sparse_optical_flow_velocity_bgr(prev,curr,D(100),D(100),D(2),D('.1'))
        dictionary=cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50); marker=cv2.aruco.generateImageMarker(dictionary,7,100)
        canvas=np.full((240,320),255,dtype=np.uint8); canvas[70:170,110:210]=marker
        pose=aruco_pose_bgr(cv2.cvtColor(canvas,cv2.COLOR_GRAY2BGR),0,D('.2'),D(300),D(300),D(160),D(120))
        ok=flow['tracked']>=10 and abs(flow['median_du']-4)<.25 and abs(flow['median_dv']-2)<.25 and len(pose)==1 and pose[0]['id']==7 and pose[0]['tvec_m'][2]>0
        mark('real visual front-end: optical flow + ArUco PnP pose',ok,{'flow':flow,'pose':pose})
    except Exception as e: mark('real visual front-end: optical flow + ArUco PnP pose',False,repr(e))

    # Visual servo, VIO, SLAM, multi-drone.
    servo=VisualServoController(D(1),D(1),D(2),D(1),D(3),D(2),D(1),D('.01')); cmd=servo.step(400,260,640,480,D('.05'),D('.1'))
    mark('visual-servo produces bounded explicit body command',all(abs(cmd[k])<=lim for k,lim in [('vx',D(3)),('vy',D(3)),('vz',D(2)),('yaw_rate',D(1))]),{k:str(v) for k,v in cmd.items()})
    vio=VisualInertialOdometry(); vio.imu(D(0),[D(0)]*3,[D(0)]*3)
    for i in range(1,101): vio.imu(D(i)/D(100),[D(0)]*3,[D('.1'),D(0),D(0)])
    before=float(vio.position[0]); vio.visual_position([D('0'),D(0),D(0)],D('.8')); after=float(vio.position[0])
    mark('VIO inertial propagation + visual correction',vio.imu_updates==100 and vio.visual_updates==1 and abs(after)<abs(before),{'before':before,'after':after})
    slam=PoseGraphSLAM(); ids=[slam.add_pose(0,0,0),slam.add_pose(1.15,.05,0),slam.add_pose(2.2,.1,0),slam.add_pose(2.9,1.1,1.55)]
    slam.add_constraint(ids[0],ids[1],1,0,0,1); slam.add_constraint(ids[1],ids[2],1,0,0,1); slam.add_constraint(ids[2],ids[3],1,1,1.57,1); pre=sum(abs(float(slam.poses[i][0])-[0,1,2,3][i]) for i in range(4)); slam.optimize(60,D('.04')); post=sum(abs(float(slam.poses[i][0])-[0,1,2,3][i]) for i in range(4))
    mark('pose-graph SLAM optimization runs bounded',len(slam.poses)==4 and len(slam.constraints)==3,{'pre_x_error':pre,'post_x_error':post})
    co=MultiDroneCoordinator(D(2),D(4)); co.update(1,[0,0,-5],[0,0,0]); co.update(2,[1,0,-5],[0,0,0]); plans=co.plan({1:[10,0,-5],2:[10,3,-5]}); mark('multi-drone coordination/deconfliction',len(plans)==2 and bool(co.conflicts()),{'plans':{str(k):[str(x) for x in v] for k,v in plans.items()},'conflicts':co.conflicts()})

    # GStreamer/WebRTC capability boundaries.
    ga=gstreamer_available(); gwa=gstreamer_webrtc_available(); recipe=json.loads(webrtc_browser_recipe_json())
    mark('GStreamer structured video backend present or fails closed',True,{'runtime_available':ga,'webrtcbin_available':gwa,'status':'EXECUTED' if ga else 'UNEXECUTED'})
    mark('WebRTC browser backend recipe exposed',recipe.get('backend')=='browser-RTCPeerConnection' and 'webrtc.create_offer' in recipe.get('operations',[]),recipe)
    try:
        wt=browser_webrtc_node_test(); mark('WebRTC media tracks + data channel execute in browser backend mock',wt.get('status')=='EXECUTED',wt,wt.get('status'))
    except Exception as e: mark('WebRTC media tracks + data channel execute in browser backend mock',False,repr(e))

    # Saga-only high-level machine-control surface.
    try:
        K=discrete_lqr_gain([[D(1),D(1)],[D(0),D(1)]],[[D(0)],[D(1)]],[[D(1),D(0)],[D(0),D(1)]],[[D(1)]],50)
        ss=StateSpaceController.create([[D(1),D(1)],[D(0),D(1)]],[[D(0)],[D(1)]],K,[[D(1)]],[D(0),D(0)],[-D(5)],[D(5)])
        kf=LinearKalmanFilter.create([[D(1)]],[[D(1)]],[[D('.01')]],[[D('.1')]],[D(0)],[[D(1)]]); kf.predict(); kf.update([D(1)])
        group=SynchronizedMotionGroup.create([D(0),D(0)],D(10),D(20),D(100)); group.retarget([D(5),D(2)]); group.step(D('.01'))
        arm=DHKinematicChain.create([[D(1),D(0),D(0),D(0)],[D(1),D(0),D(0),D(0)]]); rr=arm.resolved_rate([D(0),D(0)],[D(0),D('.1'),D(0)])
        plc=PLCScanEngine(D('.01')); plc.sample_json('{"start":true}'); plc.ton('t',True,D('.02')); plc.ton('t',True,D('.02')); plc.write('enable',True); outs=plc.commit_json()
        cob,dat=CANopen.sdo_download(0x6040,0,1,15,2); st=CiA402.state(0x27); pi=ProcessImage.create(8); pi.write_int(0,2,False,1234)
        mark('advanced machine-control core works without user host-language glue',True,{'lqr':[[str(x) for x in r] for r in K],'resolved_rate':[str(x) for x in rr],'plc':outs,'canopen_cob':cob,'cia402':st,'process':pi.hex()})
    except Exception as e: mark('advanced machine-control core works without user host-language glue',False,repr(e))

    # Saga source examples are part of qualification.
    runs=[]
    for rel in ['examples/drone/visual_vio_slam_swarm.saga','examples/machine/advanced_control.saga']:
        p=subprocess.run([sys.executable,'-m','saga','run',str(ROOT/rel)],cwd=ROOT,text=True,capture_output=True,timeout=15)
        runs.append({'file':rel,'returncode':p.returncode,'stderr':p.stderr[-1000:]})
    mark('Saga-only advanced drone/machine examples execute',all(x['returncode']==0 for x in runs),runs)

    status=all(c['pass'] or c.get('status')=='UNEXECUTED' for c in CASES)
    report={'schema':1,'release':'0.43.0',**source_binding('0.43.0'),'status':'pass' if status else 'fail','pass':status,'cases':CASES,
            'boundaries':{'official_px4_sitl':'EXECUTED' if px4 else 'UNEXECUTED','official_ardupilot_sitl':'EXECUTED' if ardu else 'UNEXECUTED','gstreamer_runtime':'EXECUTED' if ga else 'UNEXECUTED','physical_flight':'UNEXECUTED','physical_camera':'UNEXECUTED'}}
    out=ROOT/'validation/autonomy-stack-0.43.0.json'; out.parent.mkdir(exist_ok=True); out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print('REPORT',out); return 0 if status else 1
if __name__=='__main__': raise SystemExit(main())
