from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.virtual_hil_qualification_048 import (
    qualify_canfd,
    qualify_encoder,
    qualify_ethercat_dc,
    qualify_foc,
    qualify_mcu_codegen,
    qualify_safety,
    qualify_timestamping,
)


class VirtualHIL048Tests(unittest.TestCase):
    def test_foc_motor_inverter_model(self): self.assertEqual(qualify_foc()["status"], "PASS")
    def test_absolute_encoder_model(self): self.assertEqual(qualify_encoder()["status"], "PASS")
    def test_canfd_brs_model(self): self.assertEqual(qualify_canfd()["status"], "PASS")
    def test_ethercat_dc_model(self): self.assertEqual(qualify_ethercat_dc()["status"], "PASS")
    def test_timestamp_model_and_kernel_software_timestamping(self): self.assertEqual(qualify_timestamping()["status"], "PASS")
    def test_mcu_codegen_has_no_allocator_or_calls(self):
        with tempfile.TemporaryDirectory() as td:
            result = qualify_mcu_codegen(Path(td))
            self.assertEqual(result["status"], "PASS", result)
            self.assertEqual(result["allocator_symbol_references"], [])
            self.assertEqual(result["subroutine_call_instructions"], [])
            self.assertFalse(result["formal_target_wcet_proven"])
    def test_sto_estop_fault_injection_model(self): self.assertEqual(qualify_safety()["status"], "PASS")


if __name__ == "__main__": unittest.main()
