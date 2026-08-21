from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import json
import tempfile
import tomllib

from .api import compile_file
from .aot import build_standard_bundle
from .capability_audit import MODULE_CAPABILITIES
from . import ast_nodes as ast
from .linter import lint_program
from .package import pack_project, verify_lock
from .project import SagaProject, find_project, saga_files
from .workspace import SagaWorkspace, load_workspace


@dataclass(frozen=True, slots=True)
class Gate:
    name: str
    status: str
    detail: str


@dataclass(frozen=True, slots=True)
class ProjectProductionReport:
    project: str
    version: str
    root: str
    source_sha256: str
    capabilities: tuple[str, ...]
    gates: tuple[Gate, ...]

    @property
    def ready(self) -> bool:
        return all(g.status == "PASS" for g in self.gates)


def _source_digest(project: SagaProject) -> str:
    h = sha256()
    for path in saga_files(project.root):
        rel = path.relative_to(project.root).as_posix().encode("utf-8")
        data = path.read_bytes()
        h.update(len(rel).to_bytes(4, "big")); h.update(rel)
        h.update(len(data).to_bytes(8, "big")); h.update(data)
    return h.hexdigest()


def _compile_and_lint(project: SagaProject) -> tuple[Gate, tuple[str, ...]]:
    capabilities: set[str] = set()
    errors: list[str] = []
    files = saga_files(project.root)
    if not files:
        return Gate("compile-and-standard-lint", "FAIL", "project contains no Saga source"), ()
    for path in files:
        try:
            loaded = compile_file(str(path))
            for item in lint_program(loaded.program, standard=True):
                if item.severity == "error":
                    errors.append(f"{path.relative_to(project.root)}:{item.code}")
            for stmt in loaded.program.statements:
                if isinstance(stmt, ast.UseStmt) and stmt.source_path is None:
                    capabilities.update(MODULE_CAPABILITIES.get(stmt.module.lexeme, set()))
        except Exception as exc:
            errors.append(f"{path.relative_to(project.root)}:{type(exc).__name__}:{exc}")
    if errors:
        return Gate("compile-and-standard-lint", "FAIL", "; ".join(errors[:8])), tuple(sorted(capabilities))
    return Gate("compile-and-standard-lint", "PASS", f"{len(files)} source file(s) checked"), tuple(sorted(capabilities))


def _lock_gate(project: SagaProject) -> Gate:
    ok, errors = verify_lock(project.root)
    return Gate("locked-inputs", "PASS" if ok else "FAIL", "saga.lock matches project inputs" if ok else "; ".join(errors[:8]))


def _package_repro_gate(project: SagaProject) -> Gate:
    try:
        with tempfile.TemporaryDirectory(prefix="saga-prod-a-") as a, tempfile.TemporaryDirectory(prefix="saga-prod-b-") as b:
            pa = pack_project(project.root, Path(a) / f"{project.name}.sagapkg")
            pb = pack_project(project.root, Path(b) / f"{project.name}.sagapkg")
            ha, hb = sha256(pa.read_bytes()).hexdigest(), sha256(pb.read_bytes()).hexdigest()
        if ha != hb:
            return Gate("reproducible-package", "FAIL", f"package hashes differ: {ha} != {hb}")
        return Gate("reproducible-package", "PASS", ha)
    except Exception as exc:
        return Gate("reproducible-package", "FAIL", f"{type(exc).__name__}: {exc}")



def _native_repro_gate(project: SagaProject) -> Gate:
    try:
        with tempfile.TemporaryDirectory(prefix="saga-native-a-") as a, tempfile.TemporaryDirectory(prefix="saga-native-b-") as b:
            pa = Path(a) / "program"
            pb = Path(b) / "program"
            build_standard_bundle(project.entry, "native", pa)
            build_standard_bundle(project.entry, "native", pb)
            ha, hb = sha256(pa.read_bytes()).hexdigest(), sha256(pb.read_bytes()).hexdigest()
        if ha != hb:
            return Gate("reproducible-native", "FAIL", f"native hashes differ: {ha} != {hb}")
        return Gate("reproducible-native", "PASS", ha)
    except Exception as exc:
        return Gate("reproducible-native", "FAIL", f"{type(exc).__name__}: {exc}")



def _explicit_control_contract_gate(project: SagaProject) -> Gate:
    """Production machine projects must use explicit rate/budget contracts."""
    ticks = 0
    failures: list[str] = []
    for path in saga_files(project.root):
        try:
            loaded = compile_file(str(path))
        except Exception as exc:
            return Gate("explicit-control-contracts", "FAIL", f"{path.name}: {type(exc).__name__}: {exc}")
        for stmt in loaded.program.statements:
            if not isinstance(stmt, ast.FunctionDecl):
                continue
            anns = [a for a in stmt.annotations if a.name.lexeme == "control_tick"]
            if not anns:
                continue
            ticks += 1
            a = anns[0]
            if len(a.arguments) != 2:
                failures.append(f"{path.relative_to(project.root)}:{stmt.name.lexeme}: @control_tick requires (rate_hz,budget_us) for machine GA")
    if not ticks:
        return Gate("explicit-control-contracts", "FAIL", "no @control_tick function found")
    if failures:
        return Gate("explicit-control-contracts", "FAIL", "; ".join(failures[:8]))
    return Gate("explicit-control-contracts", "PASS", f"{ticks} control tick(s) use explicit timing contracts")


def _safe_evidence_path(root: Path, value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    raw = Path(value)
    if raw.is_absolute():
        return None
    root_real = root.resolve()
    p = (root / raw).resolve()
    try:
        p.relative_to(root_real)
    except ValueError:
        return None
    if p.is_symlink() or not p.is_file():
        return None
    return p


def _load_bound_evidence(path: Path, expected_kind: str, source_sha: str) -> tuple[bool, str]:
    try:
        d = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return False, f"{path.name}: malformed JSON: {exc}"
    if not isinstance(d, dict):
        return False, f"{path.name}: evidence must be an object"
    if d.get("schema") != 1 or d.get("kind") != expected_kind or d.get("pass") is not True:
        return False, f"{path.name}: schema/kind/pass mismatch"
    if d.get("project_source_sha256") != source_sha:
        return False, f"{path.name}: source binding mismatch"
    if d.get("saga_release") != "0.50.0":
        return False, f"{path.name}: saga_release must be 0.50.0"
    return True, f"{path.name}: bound {expected_kind} evidence passed"


def _machine_safety_case_gate(project: SagaProject, source_sha: str) -> Gate:
    """Validate the deployment safety-case declaration and source-bound evidence.

    This does not certify a machine. It prevents a Saga project from receiving
    the machine-production-ready label without recording the external layers
    that software cannot replace (E-stop/STO/interlock/watchdog, HIL and WCET).
    """
    path = project.root / "machine-safety.toml"
    if not path.is_file() or path.is_symlink():
        return Gate("machine-safety-case", "FAIL", "machine-safety.toml is required and must be a regular non-symlink file")
    try:
        d = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return Gate("machine-safety-case", "FAIL", f"malformed machine-safety.toml: {exc}")
    cfg = d.get("safety") if isinstance(d, dict) else None
    if not isinstance(cfg, dict):
        return Gate("machine-safety-case", "FAIL", "[safety] table is required")
    if cfg.get("profile") != "machine-production-ga-1":
        return Gate("machine-safety-case", "FAIL", "safety.profile must be machine-production-ga-1")
    required_true = ("external_emergency_stop", "sto_or_interlock", "hardware_watchdog")
    missing = [k for k in required_true if cfg.get(k) is not True]
    if missing:
        return Gate("machine-safety-case", "FAIL", "required external safety controls not declared true: " + ", ".join(missing))
    target = cfg.get("target")
    if target not in {"rtos", "mcu", "preempt_rt", "qualified-motion-controller"}:
        return Gate("machine-safety-case", "FAIL", "safety.target must name a deterministic control target")
    details: list[str] = []
    for key, kind in (("hazard_analysis", "hazard-analysis"), ("wcet_evidence", "wcet"), ("hil_evidence", "hil")):
        ep = _safe_evidence_path(project.root, cfg.get(key))
        if ep is None:
            return Gate("machine-safety-case", "FAIL", f"{key} must reference a confined regular evidence JSON file")
        ok, detail = _load_bound_evidence(ep, kind, source_sha)
        if not ok:
            return Gate("machine-safety-case", "FAIL", detail)
        details.append(detail)
    return Gate("machine-safety-case", "PASS", "; ".join(details))


def check_project(project: SagaProject, *, native: bool = False, machine: bool = False) -> ProjectProductionReport:
    compile_gate, capabilities = _compile_and_lint(project)
    gates_list = [compile_gate, _lock_gate(project), _package_repro_gate(project)]
    if native:
        gates_list.append(_native_repro_gate(project))
    if machine:
        source_sha = _source_digest(project)
        gates_list.append(_explicit_control_contract_gate(project))
        gates_list.append(_machine_safety_case_gate(project, source_sha))
    gates = tuple(gates_list)
    return ProjectProductionReport(
        project=project.name,
        version=project.version,
        root=str(project.root),
        source_sha256=_source_digest(project),
        capabilities=capabilities,
        gates=gates,
    )


def _report_dict(report: ProjectProductionReport) -> dict[str, object]:
    data = asdict(report)
    data["ready"] = report.ready
    return data


def production_check(value: str | Path = ".", *, native: bool = False, machine: bool = False) -> dict[str, object]:
    target = Path(value).expanduser().absolute()
    workspace_file = target / "saga-workspace.toml" if target.is_dir() else target.parent / "saga-workspace.toml"
    projects: list[SagaProject]
    workspace: SagaWorkspace | None = None
    if workspace_file.is_file():
        workspace = load_workspace(workspace_file)
        projects = list(workspace.members)
    else:
        project = find_project(target)
        if project is None:
            raise ValueError("no saga.toml or saga-workspace.toml found")
        projects = [project]
    reports = [check_project(project, native=native, machine=machine) for project in projects]
    ready = all(report.ready for report in reports)
    return {
        "schema": 1,
        "profile": "Saga Production Project Gate 0.50",
        "workspace": str(workspace.root) if workspace else None,
        "native_reproducibility_required": native,
        "machine_safety_case_required": machine,
        "ready": ready,
        "projects": [_report_dict(report) for report in reports],
        "note": "Machine mode requires source-bound hazard/WCET/HIL evidence and external safety declarations. The report is a release/deployment gate, not SIL/PL certification.",
    }


def write_report(report: dict[str, object], output: str | Path) -> Path:
    target = Path(output).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
