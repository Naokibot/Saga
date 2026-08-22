from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib
import re
import unicodedata

from .unicode_profile import validate_identifier


def valid_project_name(value: str) -> bool:
    value = value.strip()
    if not value or unicodedata.normalize("NFC", value) != value:
        return False
    # Hyphen is permitted as a package-name separator; each component follows
    # the same Unicode XID profile as source identifiers. This keeps names
    # international while excluding path separators, dots, controls and bidi
    # formatting characters.
    parts = value.split("-")
    return all(part and validate_identifier(part) is None for part in parts)


SEMVER_RE = re.compile(
    r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    r"(?:-(?:0|[1-9A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


@dataclass(frozen=True, slots=True)
class SagaProject:
    root: Path
    name: str
    version: str
    language: str
    entry: Path
    test_dir: Path


def find_project(path: str | Path) -> SagaProject | None:
    # Preserve the lexical path until load_project applies symlink policy.
    # Resolving here would erase a symlinked project-root alias.
    candidate = Path(path).expanduser().absolute()
    if candidate.is_file():
        candidate = candidate.parent
    current = candidate
    while True:
        manifest = current / "saga.toml"
        if manifest.is_file():
            return load_project(manifest)
        if current.parent == current:
            return None
        current = current.parent


def _has_symlink_component(root: Path, relative: str) -> bool:
    current = root
    for part in Path(relative).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def load_project(manifest: str | Path) -> SagaProject:
    raw_path = Path(manifest).expanduser()
    if _lexical_symlink_component(raw_path) is not None:
        raise ValueError("saga.toml またはプロジェクトルートにシンボリックリンクは使用できません")
    path = raw_path.resolve()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"saga.toml を読み込めません: {exc}") from exc
    project = data.get("project")
    if not isinstance(project, dict):
        raise ValueError("saga.toml に [project] が必要です")
    name = project.get("name")
    version = project.get("version")
    language = project.get("language", "1.0")
    entry = project.get("entry", "main.saga")
    test_dir = project.get("test_dir", "tests")
    if not isinstance(name, str) or not valid_project_name(name):
        raise ValueError("project.name はNFC正規化したUnicode識別子（ハイフン区切り可）にしてください")
    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version.strip()):
        raise ValueError("project.version はSemVer形式（例: 1.2.3）にしてください")
    if language not in {"0.8", "0.9", "1.0"}: raise ValueError("project.language は対応する言語版 0.8、0.9、または 1.0 にしてください")
    if not isinstance(entry, str) or not entry.endswith(".saga"): raise ValueError("project.entry は .saga ファイルにしてください")
    if not isinstance(test_dir, str) or not test_dir.strip(): raise ValueError("project.test_dir は空でない文字列にしてください")
    root = path.parent
    if _has_symlink_component(root, entry):
        raise ValueError("project.entry にシンボリックリンクは使用できません")
    if _has_symlink_component(root, test_dir):
        raise ValueError("project.test_dir にシンボリックリンクは使用できません")
    entry_path = (root / entry).resolve()
    tests_path = (root / test_dir).resolve()
    try:
        entry_path.relative_to(root)
        tests_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("project.entry と project.test_dir はプロジェクト内にしてください") from exc
    return SagaProject(root, name.strip(), version.strip(), language, entry_path, tests_path)


def saga_files(path: str | Path) -> list[Path]:
    raw = Path(path).expanduser()
    component = _lexical_symlink_component(raw)
    if component is not None:
        raise ValueError(f"Sagaソースの列挙元にシンボリックリンクは使用できません: {component}")
    target = raw.resolve()
    if target.is_file():
        return [target] if target.suffix == ".saga" else []
    files: list[Path] = []
    for candidate in target.rglob("*.saga"):
        if ".saga-standards" in candidate.parts or ".venv" in candidate.parts:
            continue
        if candidate.is_symlink():
            raise ValueError(f"Sagaソースにシンボリックリンクは使用できません: {candidate}")
        try:
            relative = candidate.relative_to(target)
        except ValueError:
            raise ValueError(f"Sagaソースが列挙ルート外にあります: {candidate}")
        current = target
        for part in relative.parts[:-1]:
            current = current / part
            if current.is_symlink():
                raise ValueError(f"Sagaソースの親ディレクトリにシンボリックリンクは使用できません: {current}")
        files.append(candidate)
    return sorted(files)


def _lexical_symlink_component(path: Path) -> Path | None:
    """Return a user-controlled symlink component without canonicalizing it.

    Relative paths are inspected from the current working directory, which is
    exactly the lexical namespace the caller supplied.  Absolute paths under
    the current working tree are inspected the same way.  For absolute paths
    outside it, the explicitly named leaf and parent remain checked without
    rejecting platform-managed prefixes such as macOS ``/var``.
    """
    raw = path.expanduser()
    if raw.is_symlink():
        return raw
    absolute = raw.absolute()
    cwd = Path.cwd().absolute()
    try:
        relative = absolute.relative_to(cwd)
    except ValueError:
        parent = raw.parent
        return parent if parent.is_symlink() else None
    current = cwd
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            return current
    return None
