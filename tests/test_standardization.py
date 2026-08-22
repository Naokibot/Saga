from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from saga import Capabilities, compile_source, run_source
from saga.errors import LexError, RuntimeLanguageError
from saga.standards import StandardsRegistry


class SagaStandardizationTests(unittest.TestCase):
    def test_unicode_identifier_profile(self):
        output: list[str] = []
        run_source('let 合計 = 40 + 2\nprint(合計)', output=output.append)
        self.assertEqual(output, ['42'])
        with self.assertRaises(LexError):
            compile_source('let cafe\u0301 = 1')
        with self.assertRaises(LexError):
            compile_source('let value = 1\n\u202eprint(value)')

    def test_task_snapshot_rejects_native_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            source = f'''
            use db
            use task
            let connection = db.open("{root / 'test.db'}")
            fn use_connection(value: any) = 4
            let future = task.spawn(use_connection, connection)
            print(task.await(future))
            '''
            with self.assertRaises(RuntimeLanguageError) as raised:
                run_source(source, capabilities=Capabilities(db_roots=(root,)))
            self.assertIn('共有可能なSaga値ではありません', str(raised.exception))

    def test_standardization_registry_is_evidence_backed_and_tamper_evident(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'registry'
            evidence = Path(tmp) / 'consent.txt'; evidence.write_text('I consent', encoding='utf-8')
            reg = StandardsRegistry.open(root); reg.init()
            reg.nominate_leader(
                name='Example Leader', email='leader@example.org', organization='Example Org',
                country='JP', consent=evidence,
            )
            status = reg.status()
            self.assertTrue(status['criteria']['project_leader_with_consent'])
            self.assertFalse(status['ready_for_np_submission'])
            self.assertTrue(status['event_chain']['valid'])
            lines = reg.event_file.read_text(encoding='utf-8').splitlines()
            event = json.loads(lines[-1]); event['payload']['country'] = 'US'
            lines[-1] = json.dumps(event, ensure_ascii=False)
            reg.event_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
            ok, _ = reg.verify_event_chain()
            self.assertFalse(ok)

    def test_registry_rejects_tampered_evidence_and_experimental_impl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'registry'
            report = Path(tmp) / 'report.txt'; report.write_text('pass', encoding='utf-8')
            reg = StandardsRegistry.open(root); reg.init()
            reg.add_implementation(
                name='saga-go', language='Go', repository='local',
                conformance_report=report, level='experimental',
            )
            self.assertFalse(reg.status()['criteria']['independent_second_implementation'])
            reg.add_implementation(
                name='saga-go-core', language='Go', repository='local',
                conformance_report=report, level='core',
            )
            self.assertTrue(reg.status()['criteria']['independent_second_implementation'])
            stored = next(reg.evidence_dir.iterdir())
            stored.write_text('tampered', encoding='utf-8')
            status = reg.status()
            self.assertFalse(status['evidence']['valid'])
            self.assertFalse(status['criteria']['independent_second_implementation'])



if __name__ == '__main__':
    unittest.main()
