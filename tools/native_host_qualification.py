#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def project_version() -> str:
    with (ROOT / "pyproject.toml").open("rb") as fh:
        return str(tomllib.load(fh)["project"]["version"])


RELEASE = project_version()


def run(cmd, *, cwd=ROOT, timeout=180, env=None):
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=timeout,
        env=env,
    )


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def executable_format_matches(path: Path, key: str) -> tuple[bool, str]:
    head = path.read_bytes()[:4]
    if key == "linux":
        ok = head == b"\x7fELF"
        fmt = "ELF"
    elif key == "windows":
        ok = head[:2] == b"MZ"
        fmt = "PE/MZ"
    elif key == "macos":
        ok = head in {
            b"\xcf\xfa\xed\xfe",
            b"\xfe\xed\xfa\xcf",
            b"\xca\xfe\xba\xbe",
            b"\xbe\xba\xfe\xca",
        }
        fmt = "Mach-O/FAT"
    else:
        ok = False
        fmt = "unknown"
    return ok, f"expected={fmt} magic={head.hex()}"


def git_commit() -> str:
    try:
        proc = run(["git", "rev-parse", "HEAD"], timeout=10)
        return proc.stdout.strip() if proc.returncode == 0 else ""
    except Exception:
        return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    ap.add_argument("--expected-host", choices=["linux", "windows", "macos"])
    ap.add_argument(
        "--source-manifest",
        help=(
            "Optional frozen release manifest to verify. Active-branch CI normally "
            "records the current source tree instead of requiring an old frozen manifest."
        ),
    )
    args = ap.parse_args()

    system_name = platform.system()
    key = {"Linux": "linux", "Windows": "windows", "Darwin": "macos"}.get(system_name)
    checks: list[dict[str, object]] = []

    def mark(name: str, ok: bool, detail: object = "") -> bool:
        checks.append({"name": name, "pass": bool(ok), "detail": str(detail)})
        return bool(ok)

    source_tree = ""
    manifest_sha = ""
    binary_sha = ""

    if key is None:
        mark("supported native host", False, system_name)
    elif args.expected_host is not None and args.expected_host != key:
        mark(
            "actual native host matches requested host",
            False,
            f"actual={key} expected={args.expected_host}",
        )
    else:
        mark(
            "actual native host matches requested host",
            True,
            f"actual={key} expected={args.expected_host or key}",
        )

        try:
            from review_evidence import build_manifest, verify_manifest

            current = build_manifest(ROOT)
            source_tree = current["tree_sha256"]
            mark("current source tree recorded", bool(source_tree), source_tree)

            if args.source_manifest:
                manifest = Path(args.source_manifest)
                if manifest.is_file():
                    ok, errors, verified_current = verify_manifest(manifest, ROOT)
                    source_tree = verified_current["tree_sha256"]
                    manifest_sha = sha(manifest)
                    mark(
                        "release source manifest matches checkout",
                        ok,
                        "; ".join(errors) or source_tree,
                    )
                else:
                    mark("release source manifest matches checkout", False, "manifest missing")
        except Exception as exc:
            mark("current source tree recorded", False, exc)

        go = shutil.which("go")
        mark("Go toolchain present", bool(go), go or "go not found")
        if go:
            version = run([go, "version"])
            mark(
                "Go toolchain starts",
                version.returncode == 0,
                version.stdout.strip() + version.stderr.strip(),
            )

            tests = run(
                [go, "test", "./...", "-count=1"],
                cwd=ROOT / "implementations/go",
                timeout=240,
            )
            mark(
                "Go Native tests on target host",
                tests.returncode == 0,
                (tests.stdout + tests.stderr)[-2000:],
            )

            vet = run([go, "vet", "./..."], cwd=ROOT / "implementations/go", timeout=180)
            mark(
                "Go vet on target host",
                vet.returncode == 0,
                (vet.stdout + vet.stderr)[-1600:],
            )

            with tempfile.TemporaryDirectory(prefix=f"saga-native-{key}-") as td0:
                td = Path(td0)
                exe = td / ("saga.exe" if key == "windows" else "saga")
                build = run(
                    [go, "build", "-trimpath", "-o", str(exe), "./cmd/saga-go"],
                    cwd=ROOT / "implementations/go",
                    timeout=180,
                )
                if mark(
                    "native build on target host",
                    build.returncode == 0,
                    (build.stdout + build.stderr)[-1600:],
                ) and exe.exists():
                    binary_sha = sha(exe)
                    mark("native executable SHA-256 recorded", len(binary_sha) == 64, binary_sha)

                    fmt_ok, fmt_detail = executable_format_matches(exe, key)
                    mark("native executable format matches host", fmt_ok, fmt_detail)

                    started = run([str(exe), "--version"])
                    mark(
                        "native executable starts",
                        started.returncode == 0
                        and RELEASE in (started.stdout + started.stderr),
                        (started.stdout + started.stderr).strip(),
                    )

                    conformance = run([str(exe), "conformance", "--json"], timeout=120)
                    try:
                        report = json.loads(conformance.stdout)
                        conformance_ok = (
                            conformance.returncode == 0
                            and report.get("pass") is True
                            and report.get("implementation_version") == RELEASE
                        )
                    except Exception:
                        report = {}
                        conformance_ok = False
                    mark(
                        "native Standard Core conformance",
                        conformance_ok,
                        json.dumps(
                            {
                                k: report.get(k)
                                for k in ("passed", "total", "pass", "implementation_version")
                            },
                            sort_keys=True,
                        ),
                    )

                    src = td / "smoke.saga"
                    src.write_text(
                        "fn twice(x:int)->int=x*2\nprint(twice(21))\n",
                        encoding="utf-8",
                    )
                    checked = run([str(exe), "check", str(src)])
                    mark(
                        "native source check",
                        checked.returncode == 0 and "OK" in checked.stdout,
                        (checked.stdout + checked.stderr).strip(),
                    )

                    executed = run([str(exe), "run", str(src)])
                    mark(
                        "native source execution",
                        executed.returncode == 0 and executed.stdout == "42\n",
                        (executed.stdout + executed.stderr).strip(),
                    )

    doc = {
        "schema": 4,
        "release": RELEASE,
        "native_host": key,
        "host": {
            "system": system_name,
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "source_manifest_sha256": manifest_sha,
        "source_tree_sha256": source_tree,
        "binary_sha256": binary_sha,
        "checks": checks,
        "pass": bool(checks) and all(bool(c["pass"]) for c in checks),
    }

    output = (
        Path(args.output)
        if args.output
        else ROOT / f"validation/native-host-{key or 'unknown'}-{RELEASE}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(doc, indent=2, ensure_ascii=False))
    return 0 if doc["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
