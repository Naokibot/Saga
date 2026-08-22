from __future__ import annotations

import os
import json
import tempfile
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from saga import Capabilities, compile_source, run_source
from saga.errors import RuntimeLanguageError, TypeCheckError
from saga.native import NativeFailure


class SagaReviewFixTests(unittest.TestCase):
    def run_program(self, source: str, capabilities: Capabilities | None = None, precision: int = 80) -> list[str]:
        output: list[str] = []
        run_source(source, output=output.append, capabilities=capabilities, precision=precision)
        return output

    def test_repeat_set_at_and_int_conversion(self):
        source = '''
        let original = repeat(0, 4)
        let changed = set_at(original, 2, int("7"))
        print(original, changed)
        '''
        self.assertEqual(self.run_program(source), ["[0, 0, 0, 0] [0, 0, 7, 0]"])

    def test_int_rejects_fractional_value(self):
        with self.assertRaises(RuntimeLanguageError):
            self.run_program("print(int(3 / 2))")

    def test_port_scoped_network_permission(self):
        caps = Capabilities(net_hosts=("127.0.0.1:8080",))
        caps.require_net("127.0.0.1", 8080)
        with self.assertRaises(NativeFailure):
            caps.require_net("127.0.0.1", 8081)
        with self.assertRaises(NativeFailure):
            caps.require_net("other.example", 8080)

    def test_network_wildcard_is_explicit(self):
        caps = Capabilities(net_hosts=("*.example.com:443",))
        caps.require_net("api.example.com", 443)
        with self.assertRaises(NativeFailure):
            caps.require_net("example.com", 443)
        with self.assertRaises(NativeFailure):
            caps.require_net("badexample.com", 443)

    def test_redirect_must_also_be_allowed(self):
        class FinalHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200); self.end_headers(); self.wfile.write(b"final")
            def log_message(self, *_args): pass

        final = ThreadingHTTPServer(("127.0.0.1", 0), FinalHandler)
        final_thread = threading.Thread(target=final.serve_forever, daemon=True); final_thread.start()

        final_port = final.server_address[1]
        class RedirectHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{final_port}/")
                self.end_headers()
            def log_message(self, *_args): pass

        redirect = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
        redirect_thread = threading.Thread(target=redirect.serve_forever, daemon=True); redirect_thread.start()
        redirect_port = redirect.server_address[1]
        try:
            caps = Capabilities(net_hosts=(f"127.0.0.1:{redirect_port}",))
            output = self.run_program(
                f'''use http\ntry {{ http.get("http://127.0.0.1:{redirect_port}/") }} catch error {{ print(error.message) }}''',
                caps,
            )
            self.assertIn(str(final_port), output[0])
            self.assertIn("ネットワーク権限", output[0])
        finally:
            redirect.shutdown(); redirect.server_close(); final.shutdown(); final.server_close()

    def test_http_response_body_can_be_bounded_by_host_policy(self):
        payload = b"x" * ((8 << 20) + 1)
        class LargeHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            def log_message(self, *_args): pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), LargeHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        port = server.server_address[1]
        try:
            source = f'use http\ntry {{ http.get("http://127.0.0.1:{port}/") }} catch error {{ print(error.message) }}'
            with patch.dict(os.environ, {"SAGA_HTTP_MAX_BODY_BYTES": str(8 << 20)}):
                output = self.run_program(source, Capabilities(net_hosts=(f"127.0.0.1:{port}",)))
            self.assertIn("8388608", output[0])
        finally:
            server.shutdown(); server.server_close()

    def test_external_process_output_policy_is_optional(self):
        program = sys.executable.replace("\\", "\\\\")
        code = "import sys;sys.stdout.buffer.write(b'x'*9000000)"
        limited = f'''use process
        try {{ process.run("{program}", ["-c", {json.dumps(code)}], 10) }} catch error {{ print(error.message) }}
        '''
        with patch.dict(os.environ, {"SAGA_PROCESS_OUTPUT_LIMIT_BYTES": str(8 << 20)}):
            output = self.run_program(limited, Capabilities(allow_process=True))
        self.assertIn("8388608", output[0])

        unlimited_timeout = f'''use process
        let r = process.run("{program}", ["-c", "print(1)"], 301)
        print(map_get(r, "code", -1))
        '''
        self.assertEqual(self.run_program(unlimited_timeout, Capabilities(allow_process=True)), ["0"])

    def test_environment_variable_requires_capability(self):
        os.environ["SAGA_REVIEW_TEST"] = "ok"
        denied = self.run_program('use cloud\ntry { cloud.env("SAGA_REVIEW_TEST", "missing") } catch error { print(error.message) }')
        self.assertIn("環境変数", denied[0])
        allowed = self.run_program(
            'use cloud\nprint(cloud.env("SAGA_REVIEW_TEST", "missing"))',
            Capabilities(env_names=("SAGA_REVIEW_TEST",)),
        )
        self.assertEqual(allowed, ["ok"])

    def test_science_mean_keeps_decimal_precision(self):
        source = '''
        use science
        precision(80)
        print(science.mean([
            0.123456789012345678901234567890,
            0.123456789012345678901234567892
        ]))
        '''
        self.assertEqual(self.run_program(source), ["0.123456789012345678901234567891"])

    def test_decimal_linear_regression(self):
        source = '''
        use ml
        precision(80)
        let model = ml.linear_regression([1.0, 2.0, 3.0], [3.0, 5.0, 7.0])
        print(ml.predict(model, 10.0))
        '''
        self.assertEqual(self.run_program(source), ["21"])

    def test_ragged_matrix_rejected(self):
        source = '''
        use science
        try {
            science.matrix_multiply([[1.0, 2.0], [3.0]], [[1.0], [2.0]])
        } catch error { print(error.message) }
        '''
        self.assertIn("列数", self.run_program(source)[0])

    def test_duplicate_annotation_rejected(self):
        with self.assertRaises(TypeCheckError):
            compile_source('@tag("a")\n@tag("b")\nclass Item(let value: int) {}')

    def test_untyped_mutual_recursion_requires_return_type(self):
        source = 'fn even(n: int) = n == 0 or odd(n - 1)\nfn odd(n: int) = n != 0 and even(n - 1)'
        with self.assertRaises(TypeCheckError):
            compile_source(source)

    def test_reflection_does_not_expose_private_field(self):
        source = '''
        use reflect
        class Secret(private let hidden: text, let shown: text) {}
        let value = Secret("x", "y")
        print(reflect.fields(value))
        try { reflect.get(value, "hidden") } catch error { print(error.message) }
        '''
        output = self.run_program(source)
        self.assertEqual(output[0], "[shown]")
        self.assertIn("private", output[1])

    def test_science_dot_and_linspace_use_requested_precision(self):
        source = """
        use science
        precision(60)
        let points = science.linspace(0.0, 1.0, 4)
        print(points[1])
        print(science.dot([0.123456789012345678901234567890, 2.0], [3.0, 4.0]))
        """
        output = self.run_program(source, precision=60)
        self.assertTrue(output[0].startswith("0.333333333333333333333333333333333333333333333333"))
        self.assertEqual(output[1], "8.37037036703703703670370370367")

    def test_orm_respects_outer_transaction_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); db_path = root / "orm_tx.db"
            caps = Capabilities(db_roots=(root,))
            source = f"""
            use db
            use orm
            @table("items")
            class Item(let id: int, let price: decimal, let enabled: bool) {{}}
            let conn = db.open("{db_path}")
            orm.create_table(conn, Item)
            fn work(database: any) -> any {{
                orm.insert(database, Item(1, 1.25, true))
                throw "rollback"
            }}
            try {{ db.transaction(conn, work) }} catch error {{ print(error.message) }}
            print(len(orm.all(conn, Item)))
            orm.insert(conn, Item(2, 2.50, false))
            let item = orm.all(conn, Item)[0]
            print(item.id, item.price, item.enabled)
            db.close(conn)
            """
            output = self.run_program(source, caps)
            self.assertEqual(output, ["rollback", "0", "2 2.5 false"])

    def test_external_process_requires_permission_and_uses_no_shell(self):
        program = sys.executable.replace("\\", "\\\\")
        source = f'''
        use process
        let result = process.run("{program}", ["-c", "print(6 * 7)"], 10)
        print(map_get(result, "code", -1))
        print(map_get(result, "stdout", ""))
        '''
        with self.assertRaises(RuntimeLanguageError):
            self.run_program(source)
        output = self.run_program(source, Capabilities(allow_process=True))
        self.assertEqual(output, ["0", "42\n"])

    def test_othello_selfplay(self):
        source = (Path(__file__).parents[1] / "examples" / "othello" / "othello_selfplay.saga").read_text(encoding="utf-8")
        output = self.run_program(source, precision=50)
        self.assertEqual(output, ["OTHELLO_SELFPLAY_OK 61 63 0"])


if __name__ == "__main__":
    unittest.main()
