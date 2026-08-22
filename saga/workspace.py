from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import tomllib

from .project import SagaProject, load_project


@dataclass(frozen=True, slots=True)
class SagaWorkspace:
    root: Path
    members: tuple[SagaProject, ...]


def _inside(root: Path, candidate: Path) -> Path:
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"workspace member must remain inside workspace root: {candidate}") from exc
    return resolved


def load_workspace(value: str | Path = ".") -> SagaWorkspace:
    raw = Path(value).expanduser()
    path = raw if raw.name == "saga-workspace.toml" else raw / "saga-workspace.toml"
    path = path.absolute()
    if path.is_symlink():
        raise ValueError("saga-workspace.toml must not be a symbolic link")
    if not path.is_file():
        raise ValueError(f"saga-workspace.toml not found: {path}")
    root = path.parent.resolve()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise ValueError(f"cannot read saga-workspace.toml: {exc}") from exc
    section = data.get("workspace")
    if not isinstance(section, dict):
        raise ValueError("saga-workspace.toml requires [workspace]")
    members = section.get("members")
    if not isinstance(members, list) or not members:
        raise ValueError("workspace.members must be a non-empty array")
    projects: list[SagaProject] = []
    seen_paths: set[Path] = set()
    seen_names: set[str] = set()
    for item in members:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("workspace.members entries must be non-empty strings")
        member_raw = root / item
        if member_raw.is_symlink():
            raise ValueError(f"workspace member must not be a symbolic link: {item}")
        member = _inside(root, member_raw)
        manifest = member / "saga.toml"
        if not manifest.is_file():
            raise ValueError(f"workspace member is missing saga.toml: {item}")
        project = load_project(manifest)
        if project.root in seen_paths:
            raise ValueError(f"workspace member is duplicated: {item}")
        if project.name in seen_names:
            raise ValueError(f"workspace project name is duplicated: {project.name}")
        seen_paths.add(project.root)
        seen_names.add(project.name)
        projects.append(project)
    return SagaWorkspace(root, tuple(projects))
