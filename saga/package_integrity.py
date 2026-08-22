from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import stat
import tempfile
import tomllib
import zipfile

FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def strict_json_loads(text: str):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError(f"duplicate JSON key: {key}")
            out[key] = value
        return out
    return json.loads(text, object_pairs_hook=unique)


def _portable_relative(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ValueError("invalid package path")
    p = PurePosixPath(value)
    if p.is_absolute() or any(part in {"", ".", ".."} for part in p.parts):
        raise ValueError(f"unsafe package path: {value}")
    normalized = p.as_posix()
    if normalized != value:
        raise ValueError(f"non-canonical package path: {value}")
    return normalized


def _has_symlink_component(root: Path, relative: str) -> bool:
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return False
        if stat.S_ISLNK(mode):
            return True
    return False


def _file_hash(path: Path) -> tuple[str, int]:
    digest = sha256()
    size = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def load_and_verify_extracted_lock(
    root: str | Path,
    *,
    expected_name: str,
    expected_version: str,
    required_member: str | None = None,
) -> tuple[dict, bytes, set[str]]:
    """Verify an installed package against its own immutable lock snapshot.

    This checks the exact tracked files, sizes and hashes. The caller can then
    compare a canonical archive digest against the digest recorded by the
    dependency lock to anchor the installed directory to the originally
    downloaded/signed package.
    """
    root = Path(root).resolve()
    manifest_path = root / "saga.toml"
    lock_path = root / "saga.lock"
    if not manifest_path.is_file() or not lock_path.is_file():
        raise ValueError("installed package is missing saga.toml or saga.lock")
    if manifest_path.is_symlink() or lock_path.is_symlink():
        raise ValueError("installed package metadata may not be symbolic links")
    try:
        manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8")).get("project", {})
        lock_raw = lock_path.read_bytes()
        lock = strict_json_loads(lock_raw.decode("utf-8"))
    except Exception as exc:
        raise ValueError("installed package metadata is malformed") from exc
    if not isinstance(manifest, dict) or not isinstance(lock, dict):
        raise ValueError("installed package metadata is malformed")
    if manifest.get("name") != expected_name or manifest.get("version") != expected_version:
        raise ValueError("installed package manifest identity mismatch")
    locked_project = lock.get("project")
    if not isinstance(locked_project, dict) or locked_project.get("name") != expected_name or locked_project.get("version") != expected_version:
        raise ValueError("installed package lock identity mismatch")
    records = lock.get("files")
    if not isinstance(records, list):
        raise ValueError("installed package lock files must be an array")
    tracked: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("installed package lock contains an invalid file record")
        rel = _portable_relative(record.get("path"))
        if rel in tracked:
            raise ValueError(f"installed package lock contains duplicate path: {rel}")
        tracked.add(rel)
        if _has_symlink_component(root, rel):
            raise ValueError(f"installed package contains symbolic-link path: {rel}")
        path = root.joinpath(*PurePosixPath(rel).parts)
        try:
            path.resolve().relative_to(root)
        except ValueError as exc:
            raise ValueError(f"installed package path escapes package root: {rel}") from exc
        if not path.is_file():
            raise ValueError(f"installed package tracked file is missing: {rel}")
        actual_hash, actual_size = _file_hash(path)
        if record.get("sha256") != actual_hash or record.get("size") != actual_size:
            raise ValueError(f"installed package tracked file was modified: {rel}")
    if "saga.toml" not in tracked:
        raise ValueError("installed package lock does not track saga.toml")
    if required_member is not None:
        required_member = _portable_relative(required_member)
        if required_member not in tracked:
            raise ValueError(f"package import is not tracked by saga.lock: {required_member}")
    return lock, lock_raw, tracked


def canonical_archive_sha256(root: str | Path, lock: dict, lock_raw: bytes) -> str:
    """Reconstruct the canonical .sagapkg bytes and hash them without mutating the package."""
    root = Path(root).resolve()
    members = {"saga.lock"}
    for record in lock.get("files", []):
        members.add(_portable_relative(record.get("path")))
    digest = sha256()
    with tempfile.TemporaryFile() as backing:
        with zipfile.ZipFile(backing, "w", compression=zipfile.ZIP_STORED) as archive:
            for relative in sorted(members):
                data = lock_raw if relative == "saga.lock" else root.joinpath(*PurePosixPath(relative).parts).read_bytes()
                info = zipfile.ZipInfo(relative, FIXED_ZIP_TIME)
                info.create_system = 3
                info.external_attr = (0o100644 & 0xFFFF) << 16
                info.compress_type = zipfile.ZIP_STORED
                archive.writestr(info, data, compress_type=zipfile.ZIP_STORED)
        backing.seek(0)
        while True:
            chunk = backing.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def verify_installed_dependency(
    root: str | Path,
    *,
    expected_name: str,
    expected_version: str,
    expected_archive_sha256: str,
    required_member: str,
) -> None:
    lock, lock_raw, _ = load_and_verify_extracted_lock(
        root,
        expected_name=expected_name,
        expected_version=expected_version,
        required_member=required_member,
    )
    actual = canonical_archive_sha256(root, lock, lock_raw)
    if actual != str(expected_archive_sha256).strip().lower():
        raise ValueError("installed package no longer matches the locked registry artifact")
