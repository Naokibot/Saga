from __future__ import annotations

import json, os, shutil, socket, struct, threading, time
from decimal import Decimal as D
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from saga.stdlib.drone_control import ControlAllocator, _solve_linear
from saga.stdlib.fine_control import FineActuatorBank, FastStateSpace
from saga.stdlib.machine_advanced import StateSpaceController, PLCScanEngine, ProcessImage, CANopen, CiA402
from saga.stdlib.machine_control import ModbusTCPMaster
from saga.stdlib.media_streaming import GStreamerRTPVideo, gstreamer_backend_json, gstreamer_execute_probe
from tools.evidence_context import source_binding

CASES=[]
def mark(name, passed, evidence, status=None):
    CASES.append({'name':name,'pass':bool(passed),'status':status or ('PASS' if passed else 'FAIL'),'evidence':evidence})


def legacy_allocate(matrix, minimum, maximum, demand):
    gram=[[D(0) for _ in range(4)] for _ in range(4)]
    for row in matrix:
        for r in range(4):
            for c in range(4): gram[r][c]+=row[r]*row[c]
    dual=_solve_linear(gram,list(demand))
    return [min(maximum,max(minimum,sum((row[j]*dual[j] for j in range(4)),D(0)))) for row in matrix]


def modbus_loopback():
    regs=[0]*64; ready=threading.Event(); result={}
    srv=socket.socket(); srv.bind(('127.0.0.1',0)); srv.listen(1); port=srv.getsockname()[1]
    def server():
        ready.set(); conn,_=srv.accept(); conn.settimeout(2)
        try:
            while True:
                h=b''
                while len(h)<7:
                    c=conn.recv(7-len(h))
                    if not c: return
                    h+=c
                tx,proto,length,unit=struct.unpack('>HHHB',h); pdu=b''
                while len(pdu)<length-1: pdu+=conn.recv(length-1-len(pdu))
                fn=pdu[0]
                if fn==6:
                    addr,val=struct.unpack('>HH',pdu[1:5]); regs[addr]=val; out=pdu
                elif fn==3:
                    addr,count=struct.unpack('>HH',pdu[1:5]); vals=regs[addr:addr+count]
                    out=bytes([3,len(vals)*2])+b''.join(struct.pack('>H',v) for v in vals)
                elif fn==16:
                    addr,count,bc=struct.unpack('>HHB',pdu[1:6]); raw=pdu[6:6+bc]
                    for i in range(count): regs[addr+i]=struct.unpack('>H',raw[i*2:i*2+2])[0]
                    out=bytes([16])+struct.pack('>HH',addr,count)
                else: out=bytes([fn|0x80,1])
                conn.sendall(struct.pack('>HHHB',tx,proto,len(out)+1,unit)+out)
        finally: conn.close()
    t=threading.Thread(target=server,daemon=True); t.start(); ready.wait(1)
    m=ModbusTCPMaster('127.0.0.1',port,500,1)
    try:
        m.write_registers(4,[100,200,300,400]); vals=m.read_holding_registers(4,4)
        result={'registers':vals,'port':port}
    finally: m.close(); srv.close(); t.join(timeout=.2)
    return result


def main():
    # Official executable/model presence: never substitute the emulator for these states.
    px4=shutil.which('px4'); ardu=shutil.which('arducopter') or shutil.which('arducopter-quad')
    yolox=os.environ.get('SAGA_YOLOX_MODEL','')
    yolox_ok=bool(yolox and Path(yolox).is_file() and Path(yolox).stat().st_size>30_000_000)
    mark('Official PX4 SITL executable present', bool(px4), {'path':px4}, 'EXECUTED' if px4 else 'UNEXECUTED')
    mark('Official ArduPilot SITL executable present', bool(ardu), {'path':ardu}, 'EXECUTED' if ardu else 'UNEXECUTED')
    mark('Pretrained YOLOX asset present', yolox_ok, {'path':yolox or None}, 'EXECUTED' if yolox_ok else 'UNEXECUTED')

    # Real GStreamer library/plugin execution.
    probe=gstreamer_execute_probe(); backend=json.loads(gstreamer_backend_json())
    mark('Real GStreamer VP8/RTP pipeline executes', probe.get('status')=='EXECUTED' and probe.get('state',{}).get('state')==4, {'probe':probe,'backend':backend})
    mark('Real webrtcbin plugin loads', bool(probe.get('webrtcbin_loaded')), {'ice_transport_available':probe.get('ice_transport_available')}, 'PLUGIN_EXECUTED')
    mark('Full GStreamer WebRTC ICE transport available', bool(probe.get('ice_transport_available')), backend, 'EXECUTED' if probe.get('ice_transport_available') else 'UNEXECUTED')
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); sock.bind(('127.0.0.1',0)); sock.settimeout(2); video=GStreamerRTPVideo()
    try:
        video.start_test_sender('127.0.0.1',sock.getsockname()[1],30); packet,peer=sock.recvfrom(65535)
        mark('Real GStreamer RTP packet reaches OS UDP socket',len(packet)>12 and packet[0]>>6==2,{'bytes':len(packet),'peer':peer,'rtp_header_hex':packet[:12].hex()})
    finally: video.stop();sock.close()

    # Physical hardware inventory.
    physical={
        'camera': sorted(str(p) for p in Path('/dev').glob('video*')),
        'serial': sorted(str(p) for pattern in ('ttyUSB*','ttyACM*') for p in Path('/dev').glob(pattern)),
        'can': sorted(str(p) for p in Path('/sys/class/net').glob('can*')),
    }
    mark('Physical camera attached',bool(physical['camera']),physical,'EXECUTED' if physical['camera'] else 'UNEXECUTED')
    mark('Physical servo/PLC/fieldbus adapter attached',bool(physical['serial'] or physical['can']),physical,'EXECUTED' if physical['serial'] or physical['can'] else 'UNEXECUTED')

    # OS-level PLC/fieldbus HIL and multi-axis servo plant.
    mb=modbus_loopback(); mark('Modbus TCP PLC HIL over real loopback socket',mb['registers']==[100,200,300,400],mb,'HIL_LOOPBACK')
    a,b=socket.socketpair(); payload=bytes.fromhex(CANopen.sdo_download(0x6040,0,1,0x000f,2)[1].hex())
    try: a.sendall(payload); got=b.recv(64)
    finally:a.close();b.close()
    mark('CANopen/CiA-402 fieldbus frame crosses OS socketpair',got==payload and CiA402.controlword('enable_operation')==15,{'frame_hex':got.hex()},'HIL_LOOPBACK')
    image=ProcessImage.create(32); plc=PLCScanEngine(D('.001')); bank=FineActuatorBank(6,D('-1'),D('1'),D('0'),D('20'),D('0'))
    position=[D('0')]*6; target=[D('.8'),D('-.5'),D('.3'),D('-.2'),D('.6'),D('-.7')]
    max_err=D(0)
    for cycle in range(20_000):
        if cycle==0: bank.set_all(target)
        cmd=bank.step(D('.001'))
        for i in range(6):
            position[i] += (cmd[i]-position[i])*D('.02')
            image.write_int(i*2,2,True,int(position[i]*D(10000)))
        plc.sample_json(json.dumps({'cycle':cycle,'enable':True})); plc.write('servo_ready',True); plc.commit_json()
        max_err=max(max_err,max(abs(target[i]-position[i]) for i in range(6)))
    final_err=max(abs(target[i]-position[i]) for i in range(6))
    mark('Six-axis servo + PLC cyclic HIL completes 20k cycles',final_err<D('.001'),{'cycles':20_000,'final_error':str(final_err),'peak_error':str(max_err),'process_image_prefix':image.hex()[:48]},'HIL_LOOPBACK')

    # Benchmark cached allocator vs 0.42 algorithm.
    c=ControlAllocator.quad_x(); demand=[D('1.8'),D('.1'),D('-.1'),D('.03')]; c.allocate(demand)
    n=10_000; t=time.perf_counter()
    for _ in range(n): c.allocate(demand)
    cached=(time.perf_counter()-t)/n*1e6
    n2=1_000; t=time.perf_counter()
    for _ in range(n2): legacy_allocate(c.matrix,c.minimum,c.maximum,demand)
    legacy=(time.perf_counter()-t)/n2*1e6
    mark('Cached control allocation hot path is lighter',cached<legacy*.7,{'cached_us':cached,'legacy_us':legacy,'speedup':legacy/cached})

    # Lightweight state-space hot path correctness/perf on an 8-state controller.
    dim=8; controls=4
    A=[[D('1') if i==j else D('.001') for j in range(dim)] for i in range(dim)]
    B=[[D('.001') for _ in range(controls)] for _ in range(dim)]
    K=[[D('.01') for _ in range(dim)] for _ in range(controls)]
    N=[[D('1') if i==j else D('0') for j in range(controls)] for i in range(controls)]
    initial=[D('.1')]*dim; lo=[D('-1')]*controls; hi=[D('1')]*controls
    ref=[D('.5')]*controls; meas=[D('.2')]*dim
    fast=FastStateSpace.create(A,B,K,N,initial,lo,hi); exact=StateSpaceController.create(A,B,K,N,initial,lo,hi)
    fcmd=fast.command(ref,meas); ecmd=exact.command(ref,meas)
    n=8_000;t=time.perf_counter()
    for _ in range(n): fast.command(ref,meas)
    fast_us=(time.perf_counter()-t)/n*1e6
    n2=3_000;t=time.perf_counter()
    for _ in range(n2): exact.command(ref,meas)
    exact_us=(time.perf_counter()-t)/n2*1e6
    equal=all(abs(fcmd[i]-ecmd[i])<D('1e-12') for i in range(controls))
    mark('Fast 8-state control path matches exact command and reduces hot-loop cost',equal and fast_us<exact_us,{'fast':[str(v) for v in fcmd],'exact':[str(v) for v in ecmd],'fast_us':fast_us,'exact_us':exact_us,'speedup':exact_us/fast_us})

    hard_fail=any(not c['pass'] and c['status'] not in {'UNEXECUTED'} for c in CASES)
    report={'schema':1,'release':'0.43.0',**source_binding('0.43.0'),'status':'fail' if hard_fail else 'pass','pass':not hard_fail,'cases':CASES,
            'boundaries':{'official_px4_sitl':'EXECUTED' if px4 else 'UNEXECUTED','official_ardupilot_sitl':'EXECUTED' if ardu else 'UNEXECUTED','pretrained_yolox':'EXECUTED' if yolox_ok else 'UNEXECUTED','physical_camera':'EXECUTED' if physical['camera'] else 'UNEXECUTED','physical_machine_hardware':'EXECUTED' if physical['serial'] or physical['can'] else 'UNEXECUTED'}}
    out=ROOT/'validation/release-0.43.0.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps(report,indent=2,ensure_ascii=False))
    return 1 if hard_fail else 0
if __name__=='__main__': raise SystemExit(main())
