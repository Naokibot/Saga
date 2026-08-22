from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from fractions import Fraction
import hashlib
import json
import sysconfig
from pathlib import Path

from .sandbox import run_python_host, support
from .values import OptionValue


class PluginSandboxError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class IsolatedPluginHandle:
    name: str
    path: str
    source: str
    sha256: str
    exports: tuple[str, ...]
    sandbox_mode: str
    imports: dict[str, tuple[str, ...]]


def _wire_out(value: object) -> object:
    if isinstance(value, OptionValue):
        return {"$saga": "option", "present": value.present, "value": _wire_out(value.value) if value.present else None}
    if isinstance(value, Decimal):
        return {"$saga": "decimal", "value": str(value)}
    if isinstance(value, Fraction):
        return {"$saga": "rational", "numerator": str(value.numerator), "denominator": str(value.denominator)}
    if isinstance(value, bytes):
        return {"$saga": "bytes", "hex": value.hex()}
    if isinstance(value, datetime):
        return {"$saga": "datetime", "value": value.isoformat()}
    if isinstance(value, timedelta):
        # Avoid ``total_seconds()`` because it passes through binary floating
        # point and loses integer microseconds for sufficiently large values.
        micros = ((value.days * 86_400 + value.seconds) * 1_000_000) + value.microseconds
        return {"$saga": "duration", "microseconds": micros}
    if isinstance(value, tuple):
        return [_wire_out(v) for v in value]
    if isinstance(value, frozenset):
        return {"$saga": "set", "items": [_wire_out(v) for v in sorted(value, key=repr)]}
    if isinstance(value, dict):
        # JSON object keys are text. Preserve non-text Saga map keys explicitly.
        if all(isinstance(k, str) for k in value):
            return {k: _wire_out(v) for k, v in value.items()}
        return {"$saga": "map", "items": [[_wire_out(k), _wire_out(v)] for k, v in value.items()]}
    if value is None or isinstance(value, (bool, int, str, float)):
        return value
    raise PluginSandboxError(f"value cannot cross the isolated plugin boundary: {type(value).__name__}")


def _wire_in(value: object) -> object:
    if isinstance(value, list):
        return tuple(_wire_in(v) for v in value)
    if isinstance(value, dict):
        tag = value.get("$saga")
        if tag == "option":
            return OptionValue.some(_wire_in(value.get("value"))) if value.get("present") else OptionValue.none()
        if tag == "decimal":
            return Decimal(str(value["value"]))
        if tag == "rational":
            return Fraction(int(value["numerator"]), int(value["denominator"]))
        if tag == "bytes":
            return bytes.fromhex(str(value["hex"]))
        if tag == "datetime":
            return datetime.fromisoformat(str(value["value"]))
        if tag == "duration":
            return timedelta(microseconds=int(value["microseconds"]))
        if tag == "set":
            return frozenset(_wire_in(v) for v in value.get("items", []))
        if tag == "map":
            return {_wire_in(k): _wire_in(v) for k, v in value.get("items", [])}
        return {str(k): _wire_in(v) for k, v in value.items()}
    if value is None:
        return OptionValue.none()
    if isinstance(value, float):
        return Decimal(str(value))
    return value


def _request(source: str, filename: str, payload: dict[str, object], *, imports: dict[str, tuple[str, ...]] | None = None, timeout: float = 10.0) -> object:
    host = Path(__file__).with_name("plugin_host.py")
    bridge_paths=[]
    if imports:
        for key in ("purelib","platlib"):
            value=sysconfig.get_paths().get(key)
            if value and value not in bridge_paths: bridge_paths.append(value)
    request = {"source": source, "filename": filename, "imports": {k:list(v) for k,v in (imports or {}).items()}, "bridge_paths": bridge_paths, **payload}
    proc = run_python_host(host, json.dumps(request, ensure_ascii=False).encode("utf-8"), timeout=timeout, strict=True)
    stdout = proc.stdout.decode("utf-8", errors="replace")
    try:
        response = json.loads(stdout)
    except json.JSONDecodeError as exc:
        stderr = proc.stderr.decode("utf-8", errors="replace")
        raise PluginSandboxError(f"isolated plugin host returned invalid data (exit={proc.returncode}): {stderr[:300]}") from exc
    if not response.get("ok"):
        raise PluginSandboxError(f"{response.get('error', 'PluginError')}: {response.get('message', 'plugin failed')}")
    return response.get("result")


def load_plugin(path: Path) -> IsolatedPluginHandle:
    source = path.read_text(encoding="utf-8")
    manifest_path = path.with_suffix(".saga-plugin.json")
    imports: dict[str, tuple[str, ...]] = {}
    if manifest_path.is_file():
        try:
            manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
            raw=manifest.get("imports",{})
            if not isinstance(raw,dict): raise ValueError("imports must be an object")
            for module,names in raw.items():
                if not isinstance(module,str) or not module or not isinstance(names,list) or not all(isinstance(n,str) and n.isidentifier() and not n.startswith("_") for n in names):
                    raise ValueError("invalid allowlisted import manifest")
                imports[module]=tuple(names)
        except (OSError,ValueError,json.JSONDecodeError) as exc:
            raise PluginSandboxError(f"invalid plugin bridge manifest: {exc}") from exc
    result = _request(source, str(path), {"op": "describe"}, imports=imports)
    if not isinstance(result, dict) or not isinstance(result.get("exports"), list):
        raise PluginSandboxError("isolated plugin did not return a valid export manifest")
    exports = tuple(str(v) for v in result["exports"])
    return IsolatedPluginHandle(path.stem, str(path), source, hashlib.sha256(source.encode("utf-8")).hexdigest(), exports, support().mode, imports)


def call_plugin(handle: IsolatedPluginHandle, name: str, args: list[object]) -> object:
    if name not in handle.exports:
        raise PluginSandboxError(f"plugin function '{name}' does not exist")
    wire_args = [_wire_out(v) for v in args]
    result = _request(handle.source, handle.path, {"op": "call", "name": name, "args": wire_args}, imports=handle.imports)
    return _wire_in(result)
