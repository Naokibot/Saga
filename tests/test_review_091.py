from __future__ import annotations

import io
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from saga.api import run_source
from saga.errors import LexError
from saga.lexer import Lexer
from saga.native import Capabilities, NativeFailure
from saga.interpreter import Interpreter
from saga.stdlib import MODULES
from saga.package import build_lock, pack_project


class SagaReview091Tests(unittest.TestCase):
    def test_private_fields_do_not_leak_through_print_or_text(self):
        output: list[str] = []
        run_source(
            'class Account(private let password: text, let name: text) {}\n'
            'let a = Account("SECRET", "Aki")\n'
            'print(a)\n'
            'print(text(a))\n',
            output=output.append,
        )
        self.assertEqual(output, ['Account(name=Aki)', 'Account(name=Aki)'])
        self.assertNotIn('SECRET', '\n'.join(output))

    def test_thread_task_snapshots_global_saga_objects_without_host_locks(self):
        output: list[str] = []
        run_source(
            'use task\n'
            'class Box(var value: int) {\n'
            '  fn get() -> int { return self.value }\n'
            '  fn set(v: int) { self.value = v }\n'
            '}\n'
            'let box = Box(10)\n'
            'fn mutate_box() -> int { box.set(99); return box.get() }\n'
            'let f = task.spawn(mutate_box)\n'
            'print(task.await(f))\n'
            'print(box.get())\n',
            output=output.append,
        )
        self.assertEqual(output, ['99', '10'])

    def test_numeric_literals_use_ascii_digits(self):
        with self.assertRaises(LexError) as ctx:
            Lexer('print(١٢٣)', '<unicode-digit>').scan_tokens()
        self.assertEqual(ctx.exception.diagnostic_id, 'SAGA-L103')
        self.assertIn('ASCII 0-9', ctx.exception.message)

    def test_websocket_disables_ambient_proxy_and_redirects(self):
        class Response:
            status = 101
            headers = {}
        class Connection:
            handshake_response = Response()
            closed = False
            def close(self): self.closed = True
            def send(self, value): return None
            def recv(self): return ""

        connection = Connection()
        interpreter = Interpreter(capabilities=Capabilities(net_hosts=('example.com:443',)))
        try:
            native = MODULES['websocket'].functions['connect']
            with patch('websocket.create_connection', return_value=connection) as create:
                result = native(interpreter, ['wss://example.com/socket'])
            self.assertIs(result, connection)
            self.assertEqual(create.call_args.kwargs['redirect_limit'], 0)
            self.assertEqual(create.call_args.kwargs['http_no_proxy'], ['*'])
        finally:
            interpreter.close()

    def test_websocket_redirect_is_not_followed_without_reauthorization(self):
        class Response:
            status = 302
            headers = {'location': 'wss://other.example/socket'}
        class Connection:
            handshake_response = Response()
            closed = False
            def close(self): self.closed = True
            def send(self, value): return None
            def recv(self): return ""
        connection = Connection()
        interpreter = Interpreter(capabilities=Capabilities(net_hosts=('example.com:443',)))
        try:
            native = MODULES['websocket'].functions['connect']
            with patch('websocket.create_connection', return_value=connection):
                with self.assertRaises(NativeFailure):
                    native(interpreter, ['wss://example.com/socket'])
            self.assertTrue(connection.closed)
        finally:
            interpreter.close()

    def test_process_output_is_not_limited_by_old_16_mib_ceiling(self):
        interpreter = Interpreter(capabilities=Capabilities(allow_process=True))
        try:
            native = MODULES['process'].functions['run']
            result = native(interpreter, [
                '/usr/bin/python3',
                ('-c', 'import sys;sys.stdout.write("x"*(17*1024*1024))'),
                30,
            ])
            self.assertEqual(len(result['stdout']), 17 * 1024 * 1024)
        finally:
            interpreter.close()

    def test_package_members_use_canonical_stored_zip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'saga.toml').write_text(
                '[project]\nname="demo"\nversion="1.0.0"\nlanguage="0.9"\nentry="main.saga"\ntest_dir="tests"\n',
                encoding='utf-8',
            )
            (root / 'main.saga').write_text('print("ok")\n', encoding='utf-8')
            build_lock(root)
            package = pack_project(root)
            with zipfile.ZipFile(package) as archive:
                self.assertTrue(archive.infolist())
                self.assertTrue(all(info.compress_type == zipfile.ZIP_STORED for info in archive.infolist()))


if __name__ == '__main__':
    unittest.main()
