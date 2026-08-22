from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from saga.native_object import build_native_objects


@unittest.skipUnless(shutil.which("go") and (shutil.which("clang") or shutil.which("cc")), "Go + C toolchain required")
class NativeObjectIncremental031Tests(unittest.TestCase):
    def write(self, root: Path, name: str, text: str) -> Path:
        path = root / name
        path.write_text(text.strip() + "\n", encoding="utf-8")
        return path

    def project(self, root: Path) -> tuple[Path, Path]:
        models = self.write(root, "models.saga", '''
module models
public fn twice(value: int) -> int = value * 2
''')
        main = self.write(root, "main.saga", '''
use "models.saga" as m
print(m.twice(21))
''')
        return main, models

    def run_binary(self, path: Path) -> str:
        proc = subprocess.run([str(path)], text=True, capture_output=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc.stdout.strip()

    def test_real_relocatable_objects_incremental_compile_and_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main, models = self.project(root)
            build_dir = root / "build"
            output = root / ("app.exe" if os.name == "nt" else "app")

            first = build_native_objects(main, output, build_dir=build_dir)
            self.assertEqual(set(first.compiled_objects), {"project/main.saga", "project/models.saga"})
            self.assertTrue(first.runtime_rebuilt)
            self.assertTrue(first.linked)
            self.assertEqual(self.run_binary(output), "42")
            self.assertEqual(len(first.objects), 2)
            if shutil.which("file") and os.name != "nt":
                for obj in first.objects:
                    desc = subprocess.check_output(["file", str(obj)], text=True)
                    self.assertIn("relocatable", desc.lower())
            if shutil.which("nm") and os.name != "nt":
                # Each module object contains native registration code, not only
                # a renamed source cache blob. The linker resolves these text symbols.
                symbols = subprocess.check_output(["nm", str(first.objects[0])], text=True)
                self.assertIn("_get_source", symbols)

            second = build_native_objects(main, output, build_dir=build_dir)
            self.assertEqual(second.compiled_objects, ())
            self.assertEqual(set(second.reused_objects), {"project/main.saga", "project/models.saga"})
            self.assertFalse(second.runtime_rebuilt)
            self.assertFalse(second.startup_rebuilt)
            self.assertFalse(second.linked)

            # Implementation-only module change: only that native object is
            # rebuilt. The unchanged importer remains a cache hit; final link
            # runs because one input object changed.
            models.write_text('module models\npublic fn twice(value: int) -> int = value * 3\n', encoding="utf-8")
            third = build_native_objects(main, output, build_dir=build_dir)
            self.assertEqual(third.compiled_objects, ("project/models.saga",))
            self.assertEqual(third.reused_objects, ("project/main.saga",))
            self.assertFalse(third.runtime_rebuilt)
            self.assertFalse(third.startup_rebuilt)
            self.assertTrue(third.linked)
            self.assertEqual(self.run_binary(output), "63")

            # Public ABI change invalidates the importer object even when the
            # existing call site remains source-compatible.
            models.write_text(
                'module models\npublic fn twice(value: int) -> int = value * 3\npublic fn spare() -> int = 1\n',
                encoding="utf-8",
            )
            abi_change = build_native_objects(main, output, build_dir=build_dir)
            self.assertEqual(set(abi_change.compiled_objects), {"project/main.saga", "project/models.saga"})
            self.assertTrue(abi_change.linked)
            self.assertEqual(self.run_binary(output), "63")

            # Tampering with a cached object is detected by its content hash.
            model_obj = next(p for p in abi_change.objects if "models.saga" in p.name)
            model_obj.write_bytes(model_obj.read_bytes() + b"tamper")
            fourth = build_native_objects(main, output, build_dir=build_dir)
            self.assertEqual(fourth.compiled_objects, ("project/models.saga",))
            # The repaired object is byte-identical to the pre-tamper object, so
            # the already-linked output remains valid and a new link is unnecessary.
            self.assertFalse(fourth.linked)
            self.assertEqual(self.run_binary(output), "63")

            report = json.loads(fourth.report.read_text(encoding="utf-8"))
            self.assertEqual(report["object_count"], 2)
            self.assertEqual(report["language_version"], "0.31")

    def test_output_symlink_is_rejected_without_overwriting_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main, _ = self.project(root)
            external = root / "external.bin"
            external.write_text("keep", encoding="utf-8")
            link = root / "app"
            try:
                link.symlink_to(external)
            except OSError:
                self.skipTest("symbolic links unavailable")
            with self.assertRaises(Exception):
                build_native_objects(main, link, build_dir=root / "build")
            self.assertEqual(external.read_text(encoding="utf-8"), "keep")

    def test_incompatible_dependency_api_fails_before_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main, models = self.project(root)
            output = root / "app"
            build_dir = root / "build"
            build_native_objects(main, output, build_dir=build_dir)
            before = output.read_bytes()
            models.write_text('module models\npublic fn twice(value: text) -> text = value\n', encoding="utf-8")
            with self.assertRaises(Exception):
                build_native_objects(main, output, build_dir=build_dir)
            self.assertEqual(output.read_bytes(), before)

    def test_concurrent_builds_share_one_cache_transaction_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main, _ = self.project(root)
            build_dir = root / "build"
            output = root / ("app.exe" if os.name == "nt" else "app")
            repo = Path(__file__).resolve().parents[1]
            code = (
                "from pathlib import Path; "
                "from saga.native_object import build_native_objects; "
                "build_native_objects(Path(r'%s'), Path(r'%s'), build_dir=Path(r'%s'))"
                % (main, output, build_dir)
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = str(repo) + os.pathsep + env.get("PYTHONPATH", "")
            first = subprocess.Popen([sys.executable, "-c", code], cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            second = subprocess.Popen([sys.executable, "-c", code], cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out1, err1 = first.communicate(timeout=90)
            out2, err2 = second.communicate(timeout=90)
            self.assertEqual(first.returncode, 0, out1 + err1)
            self.assertEqual(second.returncode, 0, out2 + err2)
            self.assertEqual(self.run_binary(output), "42")
            state = json.loads((build_dir / "state.json").read_text(encoding="utf-8"))
            import hashlib
            self.assertEqual(state["output_sha256"], hashlib.sha256(output.read_bytes()).hexdigest())

    def test_output_cannot_overwrite_object_or_symlinked_build_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main, _ = self.project(root)
            build_dir = root / "build"
            first = build_native_objects(main, root / "app", build_dir=build_dir)
            protected = first.objects[0]
            before = protected.read_bytes()
            with self.assertRaises(Exception):
                build_native_objects(main, protected, build_dir=build_dir)
            self.assertEqual(protected.read_bytes(), before)

            real = root / "real-build"
            real.mkdir()
            linked = root / "linked-build"
            try:
                linked.symlink_to(real, target_is_directory=True)
            except OSError:
                self.skipTest("symbolic links unavailable")
            with self.assertRaises(Exception):
                build_native_objects(main, root / "app2", build_dir=linked)


if __name__ == "__main__":
    unittest.main()
