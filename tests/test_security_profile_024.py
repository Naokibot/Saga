from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from saga.api import compile_source, run_source


class SagaSecurityProfile024Tests(unittest.TestCase):
    def run_program(self, source: str) -> list[str]:
        output: list[str] = []
        run_source(source, output=output.append)
        return output

    def test_security_result_contract_matches_native(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "payload.txt"
            path.write_text("Saga security", encoding="utf-8")
            expected = hashlib.sha256(b"Saga security").hexdigest()
            source = f'''use security
let digest = security.file_sha256({json.dumps(str(path))})
print(is_ok(digest), unwrap_ok(digest) == {json.dumps(expected)})
let inside = security.cidr_contains("192.0.2.0/24", "192.0.2.10")
print(is_ok(inside), unwrap_ok(inside))
let bad_cert = security.certificate_info("not a certificate")
print(is_err(bad_cert))
let bad_tls = security.tls_probe("localhost", 0, "localhost", "", 100)
print(is_err(bad_tls))
'''
            compile_source(source)
            self.assertEqual(self.run_program(source), ["true true", "true true", "true", "true"])

    def test_result_values_cross_task_snapshot_boundary(self):
        source = '''
use task
fn make_result() -> result[int,text] = ok(42)
let future = task.spawn(make_result)
let value: result[int,text] = task.await(future)
print(is_ok(value), unwrap_ok(value))
'''
        compile_source(source)
        self.assertEqual(self.run_program(source), ["true 42"])

    def test_security_file_failure_is_result(self):
        source = '''use security
let missing = security.file_sha256("/definitely/not/a/saga/file")
print(is_err(missing))
let bad_cidr = security.cidr_contains("bad-cidr", "192.0.2.1")
print(is_err(bad_cidr))
'''
        compile_source(source)
        self.assertEqual(self.run_program(source), ["true", "true"])


if __name__ == "__main__":
    unittest.main()
