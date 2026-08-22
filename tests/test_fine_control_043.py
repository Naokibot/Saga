from __future__ import annotations

import json
import socket
import unittest
from decimal import Decimal as D

from saga.stdlib.drone_control import ControlAllocator, Trajectory3D
from saga.stdlib.fine_control import CyclicClock, FastStateSpace, FineActuatorBank
from saga.stdlib.media_streaming import GStreamerRTPVideo, gstreamer_backend_json, gstreamer_execute_probe


class FineControl043Tests(unittest.TestCase):
    def test_actuator_bank_limits_deadband_and_slew(self):
        bank=FineActuatorBank(4,D('-1'),D('1'),D('0'),D('2'),D('.01'))
        bank.set_all([D('1'),D('-.5'),D('.005'),D('2')])
        self.assertEqual(bank.step(D('.1')),[D('.2'),D('-.2'),D('0'),D('.2')])
        bank.zero(); self.assertEqual(bank.step(D('.1')),[D('0'),D('0'),D('0'),D('0')])

    def test_cyclic_clock_reports_soft_realtime(self):
        c=CyclicClock(200); c.wait(); c.wait(); report=json.loads(c.stats_json())
        self.assertEqual(report['frequency_hz'],200); self.assertEqual(report['cycles'],2)
        self.assertEqual(report['timing_class'],'hosted-soft-realtime')

    def test_fast_state_space_matches_expected(self):
        c=FastStateSpace.create([[1,1],[0,1]],[[0],[1]],[[D('.1'),D('.2')]],[[1]],[0,0],[-1],[1])
        self.assertEqual(c.command([1],[0,0]),[D('1.0')])
        self.assertEqual(c.predict([D('.5')]),[D('0.0'),D('0.5')])

    def test_per_axis_trajectory_limits(self):
        t=Trajectory3D.create_per_axis([D('0')]*3,[D('5'),D('5'),D('5')],[D('1'),D('2'),D('3')],[D('2'),D('3'),D('4')],[D('4'),D('5'),D('6')])
        state=t.step(D('.1'))
        self.assertLessEqual(abs(state['velocity'][0]),D('1'))
        self.assertLessEqual(abs(state['velocity'][1]),D('2'))
        self.assertLessEqual(abs(state['velocity'][2]),D('3'))

    def test_allocator_cache_survives_reconfiguration(self):
        c=ControlAllocator.quad_x(); d=[D('1.8'),D('.1'),D('-.1'),D('.03')]
        first=c.allocate(d); second=c.allocate(d); self.assertEqual(first,second)
        c.set_disabled([]); self.assertEqual(c.allocate(d),first)

    def test_real_gstreamer_c_api_pipeline(self):
        report=gstreamer_execute_probe(); self.assertEqual(report['status'],'EXECUTED')
        self.assertTrue(report['webrtcbin_loaded'])
        backend=json.loads(gstreamer_backend_json()); self.assertTrue(backend['c_api']); self.assertTrue(backend['vp8enc'])

    def test_real_gstreamer_rtp_packet_over_udp(self):
        sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM); sock.bind(('127.0.0.1',0)); sock.settimeout(2)
        video=GStreamerRTPVideo()
        try:
            video.start_test_sender('127.0.0.1',sock.getsockname()[1],30)
            packet,_=sock.recvfrom(65535)
            self.assertGreater(len(packet),12); self.assertEqual(packet[0]>>6,2)
        finally:
            video.stop(); sock.close()


if __name__=='__main__': unittest.main()
