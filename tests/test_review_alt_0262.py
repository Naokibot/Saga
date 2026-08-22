from __future__ import annotations

import hashlib
import json
import tempfile
import threading
import unittest
import zipfile
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from pathlib import Path

from saga.api import run_file
from saga.package import build_lock, pack_project, _strict_json_loads, _write_canonical_package_atomic
from saga.registry import _archive_identity, init_registry, install, keygen, publish, serve_registry
from saga.aot import AOTError, build, build_standard_bundle


class SagaAlternateReview0262Tests(unittest.TestCase):
    def _fixture(self, root: Path) -> tuple[Path, Path]:
        pkg = root / "vendor" / "math-tools" / "1.0.0"
        pkg.mkdir(parents=True)
        (pkg / "saga.toml").write_text(
            '[project]\nname="math-tools"\nversion="1.0.0"\nlanguage="1.0"\nentry="lib.saga"\ntest_dir="tests"\n',
            encoding="utf-8",
        )
        (pkg / "lib.saga").write_text("fn twice(x:int)->int=x*2\n", encoding="utf-8")
        build_lock(pkg)
        artifact = root / "math-tools.sagapkg"
        pack_project(pkg, artifact)
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        (root / "saga.dependencies.json").write_text(
            json.dumps(
                {
                    "packages": {
                        "math-tools": {
                            "version": "1.0.0",
                            "sha256": digest,
                            "path": "vendor/math-tools/1.0.0",
                        }
                    }
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / "saga.toml").write_text(
            '[project]\nname="consumer"\nversion="0.1.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n',
            encoding="utf-8",
        )
        entry = root / "main.saga"
        entry.write_text('use "pkg:math-tools/lib.saga"\nprint(twice(21))\n', encoding="utf-8")
        return pkg, entry

    def test_runtime_rejects_post_install_dependency_tampering(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg, entry = self._fixture(root)
            out: list[str] = []
            run_file(str(entry), output=out.append)
            self.assertEqual(out, ["42"])
            (pkg / "lib.saga").write_text("fn twice(x:int)->int=x*99\n", encoding="utf-8")
            with self.assertRaisesRegex(Exception, "整合性検証に失敗"):
                run_file(str(entry))

    def test_runtime_rejects_untracked_added_dependency_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg, _ = self._fixture(root)
            (pkg / "evil.saga").write_text("fn injected()->int=99\n", encoding="utf-8")
            entry = root / "untracked.saga"
            entry.write_text('use "pkg:math-tools/evil.saga"\nprint(injected())\n', encoding="utf-8")
            with self.assertRaisesRegex(Exception, "saga.lock"):
                run_file(str(entry))

    def test_runtime_rejects_duplicate_dependency_lock_keys(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _, entry = self._fixture(root)
            record = '{"version":"1.0.0","sha256":"' + ("0" * 64) + '","path":"vendor/math-tools/1.0.0"}'
            (root / "saga.dependencies.json").write_text(
                '{"packages":{"math-tools":' + record + ',"math-tools":' + record + '}}', encoding="utf-8"
            )
            with self.assertRaisesRegex(Exception, "lock"):
                run_file(str(entry))

    def test_registry_rejects_archive_whose_content_disagrees_with_lock(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "pkg"
            root.mkdir()
            (root / "saga.toml").write_text(
                '[project]\nname="stale-lock"\nversion="1.0.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n',
                encoding="utf-8",
            )
            (root / "main.saga").write_text("print(1)\n", encoding="utf-8")
            build_lock(root)
            good = pack_project(root).read_bytes()
            source = zipfile.ZipFile(__import__("io").BytesIO(good))
            buf = __import__("io").BytesIO()
            with source, zipfile.ZipFile(buf, "w") as out:
                for info in source.infolist():
                    data = source.read(info)
                    if info.filename == "main.saga":
                        data = b"print(999)\n"
                    out.writestr(info, data)
            with self.assertRaisesRegex(ValueError, "does not match saga.lock"):
                _archive_identity(buf.getvalue())

    def test_failed_pack_preserves_previous_artifact(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "saga.toml").write_text(
                '[project]\nname="atomic-pack"\nversion="1.0.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n',
                encoding="utf-8",
            )
            (root / "main.saga").write_text("print(1)\n", encoding="utf-8")
            build_lock(root)
            out = root / "release.sagapkg"
            out.write_bytes(b"previous-valid-artifact")
            with patch("saga.package.zipfile.ZipFile.writestr", side_effect=OSError("simulated write failure")):
                with self.assertRaises(OSError):
                    pack_project(root, out)
            self.assertEqual(out.read_bytes(), b"previous-valid-artifact")

    def test_failed_lock_replace_preserves_previous_lock(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "saga.toml").write_text(
                '[project]\nname="atomic-lock"\nversion="1.0.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n',
                encoding="utf-8",
            )
            (root / "main.saga").write_text("print(1)\n", encoding="utf-8")
            build_lock(root)
            before = (root / "saga.lock").read_bytes()
            (root / "main.saga").write_text("print(2)\n", encoding="utf-8")
            with patch("saga.package.os.replace", side_effect=OSError("simulated replace failure")):
                with self.assertRaises(OSError):
                    build_lock(root)
            self.assertEqual((root / "saga.lock").read_bytes(), before)

    def test_concurrent_installs_preserve_both_dependency_records(self):
        try:
            import cryptography  # noqa: F401
        except ImportError:
            self.skipTest("cryptography unavailable")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            registry = root / "registry"
            consumer = root / "consumer"
            consumer.mkdir()
            init_registry(registry, "secret", require_signatures=True)
            server = serve_registry(registry, "127.0.0.1", 0, "secret", require_signatures=True)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{server.server_address[1]}"
            metas = {}
            try:
                for name, value in (("alpha-pkg", 1), ("beta-pkg", 2)):
                    pkg = root / name
                    pkg.mkdir()
                    (pkg / "saga.toml").write_text(
                        f'[project]\nname="{name}"\nversion="1.0.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n',
                        encoding="utf-8",
                    )
                    (pkg / "main.saga").write_text(f"fn value()->int={value}\n", encoding="utf-8")
                    priv, _ = keygen(root / f"{name}.private.pem", root / f"{name}.public.pem")
                    metas[name] = publish(pkg, url, "secret", priv)
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures = [
                        pool.submit(install, url, f"{name}@1.0.0", consumer, metas[name]["publisher_fingerprint"])
                        for name in ("alpha-pkg", "beta-pkg")
                    ]
                    for future in futures:
                        future.result(timeout=30)
                doc = json.loads((consumer / "saga.dependencies.json").read_text(encoding="utf-8"))
                self.assertEqual(set(doc["packages"]), {"alpha-pkg", "beta-pkg"})
            finally:
                server.shutdown(); server.server_close()

    def test_pack_refuses_to_overwrite_project_inputs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "saga.toml").write_text(
                '[project]\nname="protect-input"\nversion="1.0.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n',
                encoding="utf-8",
            )
            source = root / "main.saga"
            source.write_text("print(1)\n", encoding="utf-8")
            build_lock(root)
            before_source = source.read_bytes()
            before_manifest = (root / "saga.toml").read_bytes()
            with self.assertRaisesRegex(Exception, "may not overwrite"):
                pack_project(root, source)
            with self.assertRaisesRegex(Exception, "may not overwrite"):
                pack_project(root, root / "saga.toml")
            self.assertEqual(source.read_bytes(), before_source)
            self.assertEqual((root / "saga.toml").read_bytes(), before_manifest)

    def test_registry_rejects_noncanonical_archive_member_path(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "pkg"
            root.mkdir()
            (root / "saga.toml").write_text(
                '[project]\nname="alias-path"\nversion="1.0.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n',
                encoding="utf-8",
            )
            (root / "main.saga").write_text("print(1)\n", encoding="utf-8")
            build_lock(root)
            good = pack_project(root).read_bytes()
            src = zipfile.ZipFile(__import__("io").BytesIO(good))
            buf = __import__("io").BytesIO()
            with src, zipfile.ZipFile(buf, "w") as out:
                for info in src.infolist():
                    name = "./main.saga" if info.filename == "main.saga" else info.filename
                    out.writestr(name, src.read(info))
            with self.assertRaisesRegex(ValueError, "canonical"):
                _archive_identity(buf.getvalue())

    def test_idempotent_install_rejects_target_relocked_after_tamper(self):
        try:
            import cryptography  # noqa: F401
        except ImportError:
            self.skipTest("cryptography unavailable")
        with tempfile.TemporaryDirectory() as td:
            base = Path(td); registry = base / "registry"; consumer = base / "consumer"; pkg = base / "pkg"
            consumer.mkdir(); pkg.mkdir()
            init_registry(registry, "secret", require_signatures=True)
            server = serve_registry(registry, "127.0.0.1", 0, "secret", require_signatures=True)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            url = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                (pkg / "saga.toml").write_text('[project]\nname="relock-pkg"\nversion="1.0.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n', encoding="utf-8")
                (pkg / "main.saga").write_text("fn value()->int=1\n", encoding="utf-8")
                priv, _ = keygen(base / "publisher.private.pem", base / "publisher.public.pem")
                meta = publish(pkg, url, "secret", priv)
                target = install(url, "relock-pkg@1.0.0", consumer, meta["publisher_fingerprint"])
                (target / "main.saga").write_text("fn value()->int=999\n", encoding="utf-8")
                build_lock(target)  # attacker also refreshes the local lock
                with self.assertRaisesRegex(ValueError, "registry artifact|downloaded registry artifact|different or unverifiable"):
                    install(url, "relock-pkg@1.0.0", consumer)
            finally:
                server.shutdown(); server.server_close()

    def test_aot_build_refuses_to_overwrite_source(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "main.saga"
            source.write_text("print(42)\n", encoding="utf-8")
            before = source.read_bytes()
            with self.assertRaisesRegex(AOTError, "may not overwrite"):
                build_standard_bundle(source, "native", source)
            self.assertEqual(source.read_bytes(), before)

    def test_failed_aot_compiler_preserves_previous_output(self):
        if __import__('os').name == 'nt':
            self.skipTest('shell-script compiler double is POSIX-only')
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root / "main.saga"; output = root / "app"; compiler = root / "fake-clang"
            source.write_text("print(42)\n", encoding="utf-8")
            output.write_bytes(b"previous-valid-build")
            compiler.write_text("#!/bin/sh\necho simulated compiler failure >&2\nexit 7\n", encoding="utf-8")
            compiler.chmod(0o755)
            with self.assertRaisesRegex(AOTError, "simulated compiler failure"):
                build(source, "native", output, clang=str(compiler))
            self.assertEqual(output.read_bytes(), b"previous-valid-build")

    def test_negative_remainder_uses_truncating_quotient(self):
        out=[]
        run_file_source = __import__('saga.api', fromlist=['run_source']).run_source
        run_file_source("print(-2 % 7, 7 % -3, -7 % -3)", output=out.append)
        self.assertEqual(out, ["-2 1 -1"])

    def test_package_writer_rechecks_lock_snapshot_before_emitting_member(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            (root/'saga.toml').write_text('[project]\nname="snapshot-pack"\nversion="1.0.0"\nlanguage="1.0"\nentry="main.saga"\ntest_dir="tests"\n',encoding='utf-8')
            source=root/'main.saga'; source.write_text('print(1)\n',encoding='utf-8')
            build_lock(root)
            lock_raw=(root/'saga.lock').read_bytes(); lock=_strict_json_loads(lock_raw.decode('utf-8'))
            records={r['path']:r for r in lock['files']}; members=sorted({'saga.lock',*records})
            source.write_text('print(2)\n',encoding='utf-8')
            out=root/'stale.sagapkg'
            with self.assertRaisesRegex(Exception,'pack中にファイルが変更'):
                _write_canonical_package_atomic(out,root,members,lock_raw=lock_raw,records=records)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
