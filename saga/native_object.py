from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import json
import os
import platform
import re
import shutil
import subprocess
import tempfile

from . import ast_nodes as ast
from .aot import AOTError, _compiler_temp_output, _reject_output_collision, _reject_symlink_output
from .file_lock import exclusive_file_lock
from .lexer import Lexer
from .module_interface import build_module_interface, load_module_interface
from .parser import Parser
from .project import _lexical_symlink_component
from .source_units import LoadedProgram, _package_dependency, load_program

OBJECT_SCHEMA = "saga.native-object.v1"
STATE_SCHEMA = "saga.incremental-native.v1"
LANGUAGE_VERSION = "0.31"
IMPLEMENTATION_VERSION = "0.31.0"


@dataclass(frozen=True, slots=True)
class NativeObjectBuildResult:
    output: Path
    build_dir: Path
    state: Path
    report: Path
    objects: tuple[Path, ...]
    compiled_objects: tuple[str, ...]
    reused_objects: tuple[str, ...]
    runtime_rebuilt: bool
    startup_rebuilt: bool
    linked: bool


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_atomic(path: Path, data: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            tmp.chmod(mode)
        except OSError:
            pass
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _command_identity(command: str, *args: str) -> str:
    try:
        proc = subprocess.run([command, *args], text=True, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as exc:
        return f"{command}:unavailable:{exc.__class__.__name__}"
    text = (proc.stdout or proc.stderr or "").strip().splitlines()
    return text[0] if text else f"{command}:exit={proc.returncode}"


def _toolchain() -> tuple[str, str]:
    clang = shutil.which("clang") or shutil.which("cc") or shutil.which("gcc")
    go = shutil.which("go")
    if not clang:
        raise AOTError("native object build requires clang/cc")
    if not go:
        raise AOTError("native object build requires Go for the Standard Core runtime archive")
    return clang, go


def _target_triple() -> str:
    return f"{platform.system().lower()}-{platform.machine().lower()}"


def _safe_name(virtual_id: str) -> str:
    base = re.sub(r"[^A-Za-z0-9_.-]+", "_", Path(virtual_id).name)[:48] or "module"
    return f"{base}-{sha256(virtual_id.encode('utf-8')).hexdigest()[:16]}"


def _symbol(virtual_id: str) -> str:
    return "saga_obj_" + sha256(virtual_id.encode("utf-8")).hexdigest()[:24]


def _virtual_id(path: Path, loaded: LoadedProgram) -> str:
    resolved = path.resolve()
    try:
        rel = resolved.relative_to(loaded.root.resolve()).as_posix()
        return "project/" + rel
    except ValueError:
        source = loaded.sources[resolved].encode("utf-8")
        digest = sha256(source).hexdigest()
        return f"external/{digest}/{resolved.name}"


def _parse_program(path: Path, source: str) -> ast.Program:
    return Parser(Lexer(source, str(path)).scan_tokens(), str(path)).parse()


def _graph_metadata(loaded: LoadedProgram) -> tuple[dict[Path, str], dict[Path, dict[str, Path]], dict[Path, str | None]]:
    ids = {path: _virtual_id(path, loaded) for path in loaded.files}
    edges: dict[Path, dict[str, Path]] = {}
    modules: dict[Path, str | None] = {}
    for path in loaded.files:
        program = _parse_program(path, loaded.sources[path])
        module_name = None
        local: dict[str, Path] = {}
        for statement in program.statements:
            if isinstance(statement, ast.ModuleDecl):
                module_name = statement.name.lexeme
            elif isinstance(statement, ast.UseStmt) and statement.source_path is not None:
                if statement.source_path.startswith("pkg:"):
                    dep = _package_dependency(loaded.root, statement.source_path).resolve()
                else:
                    dep = (path.parent / statement.source_path).resolve()
                if dep not in ids:
                    raise AOTError(f"native object graph is missing dependency {statement.source_path} from {path}")
                local[statement.source_path] = dep
        edges[path] = local
        modules[path] = module_name
    return ids, edges, modules


def _c_bytes(name: str, data: bytes) -> str:
    body = ",".join(str(v) for v in data) if data else "0"
    return f"const unsigned char {name}[] = {{{body}}};\nconst size_t {name}_len = {len(data)};\n"


def _emit_module_c(virtual_id: str, source: str, edges: dict[str, str], metadata: dict[str, object]) -> str:
    sym = _symbol(virtual_id)
    edge_bytes = _canonical_bytes(edges)
    meta_bytes = _canonical_bytes(metadata)
    id_bytes = virtual_id.encode("utf-8") + b"\x00"
    return (
        "#include <stddef.h>\n"
        + _c_bytes(sym + "_id", id_bytes)
        + _c_bytes(sym + "_source", source.encode("utf-8"))
        + _c_bytes(sym + "_edges", edge_bytes)
        + _c_bytes(sym + "_meta", meta_bytes)
        + f"const char* {sym}_get_id(void) {{ return (const char*){sym}_id; }}\n"
        + f"const unsigned char* {sym}_get_source(void) {{ return {sym}_source; }}\n"
        + f"size_t {sym}_get_source_len(void) {{ return {sym}_source_len; }}\n"
        + f"const unsigned char* {sym}_get_edges(void) {{ return {sym}_edges; }}\n"
        + f"size_t {sym}_get_edges_len(void) {{ return {sym}_edges_len; }}\n"
    )


def _emit_startup_c(entry_id: str, virtual_ids: list[str], header_name: str) -> str:
    declarations: list[str] = []
    assignments: list[str] = []
    for index, virtual_id in enumerate(virtual_ids):
        sym = _symbol(virtual_id)
        declarations.extend([
            f"extern const char* {sym}_get_id(void);",
            f"extern const unsigned char* {sym}_get_source(void);",
            f"extern size_t {sym}_get_source_len(void);",
            f"extern const unsigned char* {sym}_get_edges(void);",
            f"extern size_t {sym}_get_edges_len(void);",
        ])
        assignments.extend([
            f"    modules[{index}].id = {sym}_get_id();",
            f"    modules[{index}].source = {sym}_get_source();",
            f"    modules[{index}].source_len = {sym}_get_source_len();",
            f"    modules[{index}].edges_json = {sym}_get_edges();",
            f"    modules[{index}].edges_len = {sym}_get_edges_len();",
        ])
    return "\n".join([
        f'#include "{header_name}"',
        "#include <stddef.h>",
        *declarations,
        "",
        "int main(void) {",
        f"    SagaObjectModule modules[{max(1, len(virtual_ids))}];",
        *assignments,
        f'    return SagaRunObjectGraph("{entry_id.replace(chr(34), chr(92)+chr(34))}", modules, {len(virtual_ids)});',
        "}",
        "",
    ])


def _compile_c(clang: str, source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    temp.unlink(missing_ok=True)
    cmd = [clang, "-O2", "-std=c11", "-fdata-sections", "-ffunction-sections", "-c", str(source), "-o", str(temp)]
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.returncode:
        temp.unlink(missing_ok=True)
        raise AOTError(proc.stderr.strip() or "native object compiler failed")
    os.replace(temp, output)


def _go_runtime_fingerprint(go_root: Path, go: str, clang: str) -> str:
    h = sha256()
    h.update(b"SagaNativeObjectRuntimeV1\n")
    h.update(IMPLEMENTATION_VERSION.encode())
    h.update(b"\n" + _target_triple().encode())
    h.update(b"\n" + _command_identity(go, "version").encode())
    h.update(b"\n" + _command_identity(clang, "--version").encode())
    for path in sorted(go_root.rglob("*.go")):
        if path.name.endswith("_test.go"):
            continue
        h.update(path.relative_to(go_root).as_posix().encode() + b"\x00")
        h.update(path.read_bytes())
    h.update((go_root / "go.mod").read_bytes())
    return h.hexdigest()


def _ensure_runtime_archive(build_dir: Path, go: str, clang: str) -> tuple[Path, Path, bool, str]:
    go_root = Path(__file__).resolve().parents[1] / "implementations" / "go"
    key = _go_runtime_fingerprint(go_root, go, clang)
    runtime_dir = build_dir / "runtime" / key[:20]
    archive = runtime_dir / "libsaga_object_runtime.a"
    header = runtime_dir / "libsaga_object_runtime.h"
    manifest = runtime_dir / "runtime.json"

    def valid() -> bool:
        if not (archive.is_file() and header.is_file() and manifest.is_file()):
            return False
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            return (
                data.get("key") == key
                and data.get("archive_sha256") == _sha_file(archive)
                and data.get("header_sha256") == _sha_file(header)
            )
        except (OSError, ValueError, json.JSONDecodeError):
            return False

    if valid():
        return archive, header, False, key
    runtime_dir.mkdir(parents=True, exist_ok=True)
    with exclusive_file_lock(runtime_dir / ".build.lock"):
        if valid():
            return archive, header, False, key
        env = os.environ.copy()
        env["CGO_ENABLED"] = "1"
        env["CC"] = clang
        temp_archive = runtime_dir / f".libsaga_object_runtime.{os.getpid()}.a"
        temp_header = temp_archive.with_suffix(".h")
        temp_archive.unlink(missing_ok=True)
        temp_header.unlink(missing_ok=True)
        try:
            proc = subprocess.run(
                [go, "build", "-trimpath", "-tags", "sagaobject", "-buildmode=c-archive", "-o", str(temp_archive), "./cmd/saga-go"],
                cwd=go_root,
                env=env,
                text=True,
                capture_output=True,
            )
            if proc.returncode:
                raise AOTError(proc.stderr.strip() or "could not build Saga Standard Core runtime archive")
            if not temp_header.is_file():
                raise AOTError("Go c-archive build did not produce a runtime header")
            os.replace(temp_archive, archive)
            os.replace(temp_header, header)
        finally:
            temp_archive.unlink(missing_ok=True)
            temp_header.unlink(missing_ok=True)
        _write_atomic(manifest, _canonical_bytes({
            "schema": 1,
            "key": key,
            "archive_sha256": _sha_file(archive),
            "header_sha256": _sha_file(header),
            "go": _command_identity(go, "version"),
            "cc": _command_identity(clang, "--version"),
            "target": _target_triple(),
        }) + b"\n")
        return archive, header, True, key


def _module_abi(path: Path, module_name: str | None, loaded: LoadedProgram, smi_dir: Path) -> tuple[str, str | None]:
    source_sha = _sha_bytes(loaded.sources[path].encode("utf-8"))
    if module_name is None:
        return "legacy:" + source_sha, None
    target = smi_dir / (_safe_name(_virtual_id(path, loaded)) + ".smi.json")
    if target.is_file():
        try:
            cached = load_module_interface(target)
            if cached.get("source_sha256") == source_sha:
                return str(cached["abi_sha256"]), str(cached["build_sha256"])
        except (OSError, ValueError, json.JSONDecodeError):
            pass
    # The graph has already passed the reference checker. Rebuild only this
    # module's public interface when its own source changed; dependency ABI
    # invalidation is tracked separately by the native object manifest.
    data = build_module_interface(path, output=target, root=loaded.root, recursive=False)
    return str(data["abi_sha256"]), str(data["build_sha256"])


def _object_is_valid(manifest_path: Path, object_path: Path, object_key: str) -> bool:
    if not manifest_path.is_file() or not object_path.is_file():
        return False
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return (
        data.get("schema") == OBJECT_SCHEMA
        and data.get("object_key") == object_key
        and data.get("object_sha256") == _sha_file(object_path)
    )


def _link_command(clang: str, output: Path, startup: Path, objects: list[Path], runtime: Path) -> list[str]:
    cmd = [clang, str(startup), *map(str, objects), str(runtime), "-o", str(output)]
    if os.name != "nt":
        cmd.extend(["-pthread", "-ldl", "-lm"])
    return cmd


def _build_native_objects_impl(
    source: str | Path,
    output: str | Path | None = None,
    *,
    build_dir: str | Path | None = None,
    force: bool = False,
) -> NativeObjectBuildResult:
    """Build Standard Core as real relocatable native objects and link them.

    Each source unit becomes a platform object file consumed by the host linker.
    The object contains the verified Saga module payload plus resolved dependency
    metadata. The Standard runtime is a cached Go C-archive, so unchanged Saga
    modules do not recompile and an unchanged object set does not relink.
    """
    clang, go = _toolchain()
    source_input = Path(source).expanduser()
    loaded = load_program(source_input)
    ids, edges, module_names = _graph_metadata(loaded)

    target = _target_triple()
    root = loaded.root
    if build_dir is None:
        build_root = root / ".saga-build" / "native-object" / target
    else:
        raw_build = Path(build_dir).expanduser()
        bad_component = _lexical_symlink_component(raw_build)
        if bad_component is not None:
            raise AOTError(f"native object build directory may not use a symbolic link: {bad_component}")
        build_root = raw_build.absolute()
    build_root.mkdir(parents=True, exist_ok=True)
    objects_dir = build_root / "objects"
    generated_dir = build_root / "generated"
    smi_dir = build_root / "interfaces"
    objects_dir.mkdir(parents=True, exist_ok=True)
    generated_dir.mkdir(parents=True, exist_ok=True)
    smi_dir.mkdir(parents=True, exist_ok=True)

    runtime, runtime_header, runtime_rebuilt, runtime_key = _ensure_runtime_archive(build_root, go, clang)
    cc_identity = _command_identity(clang, "--version")

    compiled: list[str] = []
    reused: list[str] = []
    object_paths: list[Path] = []
    object_records: list[dict] = []
    virtual_ids = sorted(ids.values())
    inverse_ids = {value: path for path, value in ids.items()}
    abi_records = {
        path: _module_abi(path, module_names[path], loaded, smi_dir)
        for path in loaded.files
    }

    for virtual_id in virtual_ids:
        path = inverse_ids[virtual_id]
        source_text = loaded.sources[path]
        source_sha = _sha_bytes(source_text.encode("utf-8"))
        local_edges = {spec: ids[target_path] for spec, target_path in sorted(edges[path].items())}
        abi_sha, smi_build_sha = abi_records[path]
        dependency_abis = {spec: abi_records[target_path][0] for spec, target_path in sorted(edges[path].items())}
        key_payload = {
            "schema": OBJECT_SCHEMA,
            "language_version": LANGUAGE_VERSION,
            "implementation_version": IMPLEMENTATION_VERSION,
            "target": target,
            "virtual_id": virtual_id,
            "source_sha256": source_sha,
            "abi_sha256": abi_sha,
            "smi_build_sha256": smi_build_sha,
            "dependency_abis": dependency_abis,
            "edges": local_edges,
            "compiler": cc_identity,
        }
        object_key = _sha_bytes(_canonical_bytes(key_payload))
        safe = _safe_name(virtual_id)
        ext = ".obj" if os.name == "nt" else ".o"
        obj = objects_dir / (safe + ext)
        manifest = objects_dir / (safe + ".native.json")
        if force or not _object_is_valid(manifest, obj, object_key):
            c_path = generated_dir / (safe + ".c")
            c_path.write_text(_emit_module_c(virtual_id, source_text, local_edges, {
                "schema": OBJECT_SCHEMA,
                "language_version": LANGUAGE_VERSION,
                "virtual_id": virtual_id,
                "source_sha256": source_sha,
                "abi_sha256": abi_sha,
                "smi_build_sha256": smi_build_sha,
            }), encoding="utf-8")
            _compile_c(clang, c_path, obj)
            compiled.append(virtual_id)
            record = {
                **key_payload,
                "object_key": object_key,
                "object_sha256": _sha_file(obj),
            }
            _write_atomic(manifest, _canonical_bytes(record) + b"\n")
        else:
            reused.append(virtual_id)
            record = json.loads(manifest.read_text(encoding="utf-8"))
        object_paths.append(obj)
        object_records.append(record)

    entry_id = ids[loaded.entry]
    header_copy = generated_dir / "saga_object_runtime.h"
    if not header_copy.is_file() or _sha_file(header_copy) != _sha_file(runtime_header):
        shutil.copy2(runtime_header, header_copy)
    startup_text = _emit_startup_c(entry_id, virtual_ids, header_copy.name)
    startup_key = _sha_bytes((runtime_key + "\n" + startup_text + "\n" + cc_identity).encode("utf-8"))
    startup_ext = ".obj" if os.name == "nt" else ".o"
    startup_obj = objects_dir / ("startup" + startup_ext)
    startup_manifest = objects_dir / "startup.native.json"
    startup_rebuilt = force
    if not force:
        try:
            sm = json.loads(startup_manifest.read_text(encoding="utf-8"))
            startup_rebuilt = not (
                sm.get("startup_key") == startup_key
                and startup_obj.is_file()
                and sm.get("object_sha256") == _sha_file(startup_obj)
            )
        except (OSError, ValueError, json.JSONDecodeError):
            startup_rebuilt = True
    if startup_rebuilt:
        startup_c = generated_dir / "startup.c"
        startup_c.write_text(startup_text, encoding="utf-8")
        startup_tmp = startup_obj.with_name(f".{startup_obj.name}.{os.getpid()}.tmp")
        startup_tmp.unlink(missing_ok=True)
        include_flag = [clang, "-O2", "-std=c11", "-c", str(startup_c), "-I", str(generated_dir), "-o", str(startup_tmp)]
        proc = subprocess.run(include_flag, text=True, capture_output=True)
        if proc.returncode:
            startup_tmp.unlink(missing_ok=True)
            raise AOTError(proc.stderr.strip() or "native startup object compiler failed")
        os.replace(startup_tmp, startup_obj)
        _write_atomic(startup_manifest, _canonical_bytes({
            "schema": OBJECT_SCHEMA,
            "startup_key": startup_key,
            "object_sha256": _sha_file(startup_obj),
        }) + b"\n")

    if output is None:
        suffix = ".exe" if os.name == "nt" else ""
        out = loaded.entry.parent / (loaded.entry.stem + suffix)
    else:
        out = Path(output).expanduser()
    _reject_symlink_output(out)
    out = out.absolute()
    _reject_output_collision(loaded.entry, out, extra_inputs=(Path(clang).resolve(), Path(go).resolve(), runtime.resolve(), startup_obj.resolve(), *tuple(p.resolve() for p in object_paths)))
    out.parent.mkdir(parents=True, exist_ok=True)

    runtime_sha = _sha_file(runtime)
    link_key = _sha_bytes(_canonical_bytes({
        "schema": STATE_SCHEMA,
        "target": target,
        "entry": entry_id,
        "runtime_sha256": runtime_sha,
        "startup_sha256": _sha_file(startup_obj),
        "objects": [record["object_sha256"] for record in object_records],
        "linker": cc_identity,
    }))
    state_path = build_root / "state.json"
    linked = True
    if not force and state_path.is_file() and out.is_file():
        try:
            old = json.loads(state_path.read_text(encoding="utf-8"))
            linked = not (
                old.get("schema") == STATE_SCHEMA
                and old.get("link_key") == link_key
                and old.get("output_sha256") == _sha_file(out)
            )
        except (OSError, ValueError, json.JSONDecodeError):
            linked = True
    if linked:
        tmp_out = _compiler_temp_output(out)
        try:
            proc = subprocess.run(_link_command(clang, tmp_out, startup_obj, object_paths, runtime), text=True, capture_output=True)
            if proc.returncode:
                raise AOTError(proc.stderr.strip() or "native object linker failed")
            os.replace(tmp_out, out)
            if os.name != "nt":
                out.chmod(out.stat().st_mode | 0o111)
        finally:
            tmp_out.unlink(missing_ok=True)

    state = {
        "schema": STATE_SCHEMA,
        "language_version": LANGUAGE_VERSION,
        "implementation_version": IMPLEMENTATION_VERSION,
        "target": target,
        "entry": entry_id,
        "runtime_key": runtime_key,
        "runtime_sha256": runtime_sha,
        "startup_key": startup_key,
        "objects": object_records,
        "link_key": link_key,
        "output_sha256": _sha_file(out),
    }
    _write_atomic(state_path, _canonical_bytes(state) + b"\n")
    report_path = build_root / "last-build.json"
    report = {
        "schema": 1,
        "language_version": LANGUAGE_VERSION,
        "target": target,
        "entry": entry_id,
        "object_count": len(object_paths),
        "compiled_objects": compiled,
        "reused_objects": reused,
        "runtime_rebuilt": runtime_rebuilt,
        "startup_rebuilt": startup_rebuilt,
        "linked": linked,
        "output": str(out),
        "output_sha256": state["output_sha256"],
    }
    _write_atomic(report_path, json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")
    return NativeObjectBuildResult(
        out, build_root, state_path, report_path, tuple(object_paths), tuple(compiled), tuple(reused), runtime_rebuilt, startup_rebuilt, linked,
    )

def build_native_objects(
    source: str | Path,
    output: str | Path | None = None,
    *,
    build_dir: str | Path | None = None,
    force: bool = False,
) -> NativeObjectBuildResult:
    """Serialize one incremental build cache across processes.

    Module objects, startup state, and the final link report form one cache
    transaction.  A build-directory lock prevents two writers from publishing
    mutually inconsistent object/manifests or state.json at the same time.
    Source files remain ordinary user inputs and are reloaded inside the lock.
    """
    source_input = Path(source).expanduser()
    loaded = load_program(source_input)
    target = _target_triple()
    if build_dir is None:
        build_root = loaded.root / ".saga-build" / "native-object" / target
    else:
        raw_build = Path(build_dir).expanduser()
        bad_component = _lexical_symlink_component(raw_build)
        if bad_component is not None:
            raise AOTError(f"native object build directory may not use a symbolic link: {bad_component}")
        build_root = raw_build.absolute()
    build_root.mkdir(parents=True, exist_ok=True)
    with exclusive_file_lock(build_root / ".incremental-build.lock"):
        return _build_native_objects_impl(
            source_input,
            output,
            build_dir=build_root,
            force=force,
        )

