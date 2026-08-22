from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import os
import tempfile
import zipfile

from .project import SagaProject, load_project
from .source_units import load_program

LOCK_SCHEMA = 1
LANGUAGE_VERSION = "0.9"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


class PackageError(ValueError):
    pass


def _reject_symlink_path(path: Path, *, label: str, base: Path | None = None) -> None:
    raw = path.expanduser()
    if raw.is_symlink():
        raise PackageError(f"{label} にシンボリックリンクは使用できません: {raw}")
    absolute = raw.absolute()
    anchor = (base or Path.cwd()).absolute()
    try:
        relative = absolute.relative_to(anchor)
    except ValueError:
        # An explicitly absolute path outside the trusted project/CWD may pass
        # through platform-managed symlinks. The named leaf was checked above.
        return
    current = anchor
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise PackageError(f"{label} にシンボリックリンクは使用できません: {current}")


@dataclass(frozen=True, slots=True)
class LockResult:
    path: Path
    data: dict


def _atomic_replace_bytes(path: Path, data: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, mode)
        with os.fdopen(fd, "wb", closefd=False) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.close(fd); fd = -1
        os.replace(tmp, path)
        if os.name != "nt":
            os.chmod(path, mode)
    finally:
        if fd >= 0:
            os.close(fd)
        tmp.unlink(missing_ok=True)


def _write_canonical_package_atomic(
    out: Path, project_root: Path, members: list[str], *, lock_raw: bytes, records: dict[str, dict]
) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{out.name}.", dir=out.parent)
    tmp = Path(tmp_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o644)
        with os.fdopen(fd, "w+b", closefd=False) as backing:
            with zipfile.ZipFile(backing, "w", compression=zipfile.ZIP_STORED) as archive:
                for relative in members:
                    if relative == "saga.lock":
                        data = lock_raw
                    else:
                        path = project_root / relative
                        data = path.read_bytes()
                        record = records.get(relative)
                        if record is None:
                            raise PackageError(f"lockにないファイルをパッケージ化できません: {relative}")
                        if record.get("size") != len(data) or record.get("sha256") != sha256(data).hexdigest():
                            raise PackageError(f"pack中にファイルが変更されました: {relative}")
                    info = zipfile.ZipInfo(relative, FIXED_ZIP_TIME)
                    info.create_system = 3
                    info.external_attr = (0o100644 & 0xFFFF) << 16
                    info.compress_type = zipfile.ZIP_STORED
                    archive.writestr(info, data, compress_type=zipfile.ZIP_STORED)
            backing.flush()
            os.fsync(backing.fileno())
        os.close(fd); fd = -1
        os.replace(tmp, out)
        if os.name != "nt":
            os.chmod(out, 0o644)
    finally:
        if fd >= 0:
            os.close(fd)
        tmp.unlink(missing_ok=True)


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _project(value: str | Path) -> SagaProject:
    raw = Path(value).expanduser()
    _reject_symlink_path(raw, label="project path")
    manifest = raw / "saga.toml" if raw.is_dir() else raw
    if manifest.name != "saga.toml":
        raise PackageError("プロジェクトのディレクトリまたはsaga.tomlを指定してください")
    # Preserve the caller's lexical path until load_project has applied the
    # project-root symlink policy; resolving first would erase that evidence.
    return load_project(manifest)


def _checked_relative(path: Path, root: Path) -> str:
    if path.is_symlink():
        raise PackageError(f"シンボリックリンクはパッケージへ含められません: {path}")
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise PackageError(f"プロジェクト外のファイルは含められません: {path}") from exc
    return relative.as_posix()


def _strict_json_loads(text: str):
    def unique(pairs):
        out={}
        for k,v in pairs:
            if k in out: raise ValueError(f"duplicate JSON key: {k}")
            out[k]=v
        return out
    return json.loads(text,object_pairs_hook=unique)


def build_lock(value: str | Path = ".") -> LockResult:
    project = _project(value)
    loaded = load_program(project.entry, root=project.root)
    paths = [project.root / "saga.toml", *loaded.files]
    unique = sorted(dict.fromkeys(path.resolve() for path in paths), key=lambda item: item.as_posix())
    records = []
    for path in unique:
        relative = _checked_relative(path, project.root)
        records.append({"path": relative, "sha256": _hash(path), "size": path.stat().st_size})
    data = {
        "schema": LOCK_SCHEMA,
        "language": "Saga",
        "language_version": project.language,
        "project": {"name": project.name, "version": project.version, "entry": project.entry.relative_to(project.root).as_posix()},
        "files": records,
    }
    lock_path = project.root / "saga.lock"
    payload = (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _atomic_replace_bytes(lock_path, payload)
    return LockResult(lock_path, data)


def verify_lock(value: str | Path = ".") -> tuple[bool, list[str]]:
    project = _project(value)
    lock_path = project.root / "saga.lock"
    try:
        data = _strict_json_loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return False, [f"saga.lockを読み込めません: {exc}"]
    errors: list[str] = []
    if data.get("schema") != LOCK_SCHEMA:
        errors.append("未対応のlock schemaです")
    if data.get("language") != "Saga" or data.get("language_version") != project.language:
        errors.append("言語名または言語版がsaga.tomlと一致しません")
    project_data = data.get("project", {})
    if project_data.get("name") != project.name or project_data.get("version") != project.version:
        errors.append("プロジェクト名または版がsaga.tomlと一致しません")
    records = data.get("files")
    if not isinstance(records, list):
        return False, [*errors, "filesは配列でなければなりません"]
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            errors.append("不正なファイル記録があります")
            continue
        relative = record["path"]
        if relative in seen:
            errors.append(f"重複したファイル記録: {relative}")
            continue
        seen.add(relative)
        path = (project.root / relative).resolve()
        try:
            path.relative_to(project.root)
        except ValueError:
            errors.append(f"プロジェクト外のパス: {relative}")
            continue
        if not path.is_file() or path.is_symlink():
            errors.append(f"ファイルがないかシンボリックリンクです: {relative}")
            continue
        actual_size = path.stat().st_size
        actual_hash = _hash(path)
        if record.get("size") != actual_size or record.get("sha256") != actual_hash:
            errors.append(f"内容がlockと一致しません: {relative}")
    try:
        expected = build_lock_snapshot(project)
    except Exception as exc:
        errors.append(f"現在のソース依存グラフを検証できません: {exc}")
        return False, errors
    expected_paths = {record["path"] for record in expected["files"]}
    if expected_paths != seen:
        for missing in sorted(expected_paths - seen):
            errors.append(f"lockに不足: {missing}")
        for extra in sorted(seen - expected_paths):
            errors.append(f"lockに不要: {extra}")
    return not errors, errors


def build_lock_snapshot(project: SagaProject) -> dict:
    loaded = load_program(project.entry, root=project.root)
    paths = sorted(dict.fromkeys([project.root / "saga.toml", *loaded.files]), key=lambda item: item.as_posix())
    return {
        "files": [
            {"path": _checked_relative(path, project.root), "sha256": _hash(path), "size": path.stat().st_size}
            for path in paths
        ]
    }


def pack_project(value: str | Path = ".", output: str | Path | None = None) -> Path:
    project = _project(value)
    try:
        lock_raw = (project.root / "saga.lock").read_bytes()
        data = _strict_json_loads(lock_raw.decode("utf-8"))
    except Exception as exc:
        raise PackageError(f"saga.lockを読み込めません: {exc}") from exc
    expected = build_lock_snapshot(project)
    if data.get("schema") != LOCK_SCHEMA or data.get("language") != "Saga" or data.get("language_version") != project.language:
        raise PackageError("lock検証に失敗しました: 言語情報が現在のprojectと一致しません")
    project_data = data.get("project") if isinstance(data, dict) else None
    if not isinstance(project_data, dict) or project_data.get("name") != project.name or project_data.get("version") != project.version or project_data.get("entry") != project.entry.relative_to(project.root).as_posix():
        raise PackageError("lock検証に失敗しました: project identityが現在のprojectと一致しません")
    actual_records = data.get("files")
    if not isinstance(actual_records, list) or actual_records != expected["files"]:
        raise PackageError("lock検証に失敗しました: saga.lock does not match current project inputs")
    if output:
        raw_out = Path(output).expanduser()
    else:
        raw_out = project.root / "dist" / f"{project.name}-{project.version}.sagapkg"
    _reject_symlink_path(raw_out, label="package output", base=project.root if not output else None)
    out = raw_out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    members = ["saga.lock", *(record["path"] for record in data["files"])]
    members = sorted(dict.fromkeys(members))
    protected = {(project.root / relative).resolve() for relative in members}
    if out in protected:
        raise PackageError(f"package output may not overwrite a project input: {out}")
    # Canonical Saga packages use uncompressed ZIP members. Write through a
    # same-directory temporary file and atomically replace the destination so
    # an interrupted pack never truncates a previously valid artifact.
    records = {record["path"]: record for record in data["files"]}
    _write_canonical_package_atomic(out, project.root, members, lock_raw=lock_raw, records=records)
    return out
