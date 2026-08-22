from __future__ import annotations

import io
import json
import unittest

from saga.lsp import LspServer, diagnostics_for_text


class SagaLsp090Tests(unittest.TestCase):
    def test_lsp_diagnostic_uses_stable_detailed_id(self):
        items = diagnostics_for_text("let score = 1\nscore = 2\n", "file:///tmp/example.saga", "en")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["code"], "SAGA-T101")
        self.assertEqual(items[0]["data"]["category"], "SAGA-T001")
        self.assertEqual(items[0]["range"]["start"], {"line": 1, "character": 0})
        self.assertIn("Fix:", items[0]["message"])

    def test_utf16_lsp_position_after_non_bmp_character(self):
        source = 'print("😀", missing)\n'
        items = diagnostics_for_text(source, "file:///tmp/emoji.saga", "en", "utf-16")
        self.assertEqual(items[0]["code"], "SAGA-T102")
        # Saga scalar column sees 😀 as one scalar; LSP UTF-16 uses two code units.
        scalar_offset = source.index("missing")
        utf16_offset = len(source[:scalar_offset].encode("utf-16-le")) // 2
        self.assertEqual(items[0]["range"]["start"]["character"], utf16_offset)

    def test_valid_document_has_no_diagnostics(self):
        self.assertEqual(diagnostics_for_text("let score = 1\nprint(score)\n", "file:///tmp/example.saga", "ja"), [])

    def test_initialize_advertises_full_sync(self):
        out = io.BytesIO()
        server = LspServer(language="en", instream=io.BytesIO(), outstream=out)
        keep = server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertTrue(keep)
        raw = out.getvalue()
        body = raw.split(b"\r\n\r\n", 1)[1]
        message = json.loads(body.decode("utf-8"))
        from saga import __version__
        self.assertEqual(message["result"]["serverInfo"]["version"], __version__)
        self.assertEqual(message["result"]["capabilities"]["textDocumentSync"]["change"], 1)
        self.assertEqual(message["result"]["capabilities"]["positionEncoding"], "utf-16")


if __name__ == "__main__":
    unittest.main()
