from __future__ import annotations

import json
import time
import unittest
from decimal import Decimal as D

from saga.stdlib.drone_control import ControlAllocator
from saga.stdlib.fine_control import CyclicClock, FastStateSpace, FineActuatorBank


class Control4kHz044Tests(unittest.TestCase):
    def test_kernel_timer_counts_4000_ticks_per_second(self):
        clock = CyclicClock(4000)
        try:
            start = time.perf_counter()
            total = 0
            while total < 4000:
                total += clock.wait_due()
            elapsed = time.perf_counter() - start
            report = json.loads(clock.stats_json())
            self.assertGreaterEqual(total, 4000)
            self.assertLess(elapsed, 1.20)
            self.assertAlmostEqual(report["period_us"], 250.0, places=3)
            if report["backend"] == "linux-timerfd":
                self.assertLess(abs((total / elapsed) - 4000), 80)
        finally:
            clock.close()

    def test_control_hot_path_fits_250us_budget_at_p99(self):
        bank = FineActuatorBank(8, D("-1"), D("1"), D("0"), D("10000"), D("0"))
        bank.set_all([D(".5")] * 8)
        allocator = ControlAllocator.quad_x()
        desired = [D("1.8"), D(".1"), D("-.1"), D(".03")]
        state = FastStateSpace.create(
            [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
            [[1], [1], [1], [1]], [[D(".1")] * 4], [[1]],
            [0] * 4, [-1], [1],
        )
        latency_us = []
        for _ in range(5000):
            start = time.perf_counter_ns()
            allocator.allocate(desired)
            state.command([D(".5")], [D("0")] * 4)
            bank.step(D(".00025"))
            latency_us.append((time.perf_counter_ns() - start) / 1000.0)
        latency_us.sort()
        p99 = latency_us[int(len(latency_us) * 0.99)]
        self.assertLess(p99, 250.0)


if __name__ == "__main__":
    unittest.main()
