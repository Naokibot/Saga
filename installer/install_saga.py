#!/usr/bin/env python3
"""Offline, user-scoped installer for Saga.

This installer does not download or execute remote code. It verifies the bundled
wheel, creates an isolated virtual environment, and installs Saga into it.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import venv

VERSION = "0.10.1"
WHEEL_NAME = f"saga_language-{VERSION}-py3-none-any.whl"


def default_prefix() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "Saga"
    return Path.home() / ".local" / "share" / "saga"


def default_bin_dir() -> Path:
    if os.name == "nt":
        return default_prefix() / "bin"
    return Path.home() / ".local" / "bin"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def venv_python(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def venv_saga(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts/saga.exe" if os.name == "nt" else "bin/saga")


def write_launcher(bin_dir: Path, saga_exe: Path) -> Path:
    bin_dir.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        launcher = bin_dir / "saga.cmd"
        launcher.write_text(f'@echo off\r\n"{saga_exe}" %*\r\n', encoding="utf-8")
    else:
        launcher = bin_dir / "saga"
        launcher.write_text(f'#!/bin/sh\nexec "{saga_exe}" "$@"\n', encoding="utf-8")
        launcher.chmod(0o755)
    return launcher


def verify_manifest(bundle: Path, wheel: Path) -> None:
    manifest_path = bundle / "manifest.json"
    if not manifest_path.exists():
        raise RuntimeError("manifest.json が見つかりません")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = manifest.get("files", {}).get(wheel.name)
    if not expected:
        raise RuntimeError(f"manifestに {wheel.name} がありません")
    actual = sha256(wheel)
    if actual != expected:
        raise RuntimeError(f"wheelのSHA-256が一致しません\nexpected={expected}\nactual={actual}")


def install(args: argparse.Namespace) -> int:
    if sys.version_info < (3, 13):
        raise RuntimeError("Saga 0.9にはPython 3.13以上が必要です")

    bundle = Path(__file__).resolve().parent
    wheel = bundle / WHEEL_NAME
    if not wheel.exists():
        raise RuntimeError(f"インストールファイルが見つかりません: {wheel}")
    verify_manifest(bundle, wheel)

    prefix = Path(args.prefix).expanduser().resolve()
    bin_dir = Path(args.bin_dir).expanduser().resolve()
    venv_dir = prefix / "venv"

    if args.force and venv_dir.exists():
        shutil.rmtree(venv_dir)
    prefix.mkdir(parents=True, exist_ok=True)

    if not venv_python(venv_dir).exists():
        venv.EnvBuilder(with_pip=True, clear=False).create(venv_dir)

    command = [str(venv_python(venv_dir)), "-m", "pip", "install", "--no-deps", "--force-reinstall", str(wheel)]
    subprocess.run(command, check=True)

    examples_source = bundle / "examples"
    examples_target = prefix / "examples"
    if examples_target.exists(): shutil.rmtree(examples_target)
    if examples_source.exists(): shutil.copytree(examples_source, examples_target)

    launcher = write_launcher(bin_dir, venv_saga(venv_dir))
    version = subprocess.check_output([str(launcher), "--version"], text=True).strip()
    if version != f"Saga {VERSION}":
        raise RuntimeError(f"インストール後の検証に失敗しました: {version}")

    selfplay = examples_target / "othello" / "othello_selfplay.saga"
    if selfplay.exists():
        output = subprocess.check_output([str(launcher), "run", str(selfplay)], text=True).strip()
        if not output.startswith("OTHELLO_SELFPLAY_OK"):
            raise RuntimeError(f"オセロ自己対戦の検証に失敗しました: {output}")

    print(f"Saga {VERSION} をインストールしました")
    print(f"Launcher: {launcher}")
    print(f"Runtime:  {venv_dir}")
    if str(bin_dir) not in os.environ.get("PATH", "").split(os.pathsep):
        print(f"PATHに追加してください: {bin_dir}")
    return 0


def uninstall(args: argparse.Namespace) -> int:
    prefix = Path(args.prefix).expanduser().resolve()
    bin_dir = Path(args.bin_dir).expanduser().resolve()
    launcher = bin_dir / ("saga.cmd" if os.name == "nt" else "saga")
    if launcher.exists(): launcher.unlink()
    if prefix.exists(): shutil.rmtree(prefix)
    print(f"Sagaを削除しました: {prefix}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Saga offline installer")
    parser.add_argument("--prefix", default=str(default_prefix()), help="Saga本体のインストール先")
    parser.add_argument("--bin-dir", default=str(default_bin_dir()), help="sagaランチャーの配置先")
    parser.add_argument("--force", action="store_true", help="既存ランタイムを作り直す")
    parser.add_argument("--uninstall", action="store_true", help="Sagaを削除する")
    args = parser.parse_args()
    try:
        return uninstall(args) if args.uninstall else install(args)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"インストールエラー: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
