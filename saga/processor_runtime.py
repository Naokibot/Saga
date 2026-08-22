from __future__ import annotations
import json
from pathlib import Path
from .sandbox import run_python_host

class ProcessorSandboxError(RuntimeError): pass

def run_processor(path: Path, metadata: dict, *, timeout: float=10.0) -> dict[str,str]:
    source=path.read_text(encoding="utf-8")
    host=Path(__file__).with_name("processor_host.py")
    payload=json.dumps({"source":source,"filename":str(path),"metadata":metadata},ensure_ascii=False).encode("utf-8")
    proc=run_python_host(host,payload,timeout=timeout,strict=True)
    try: response=json.loads(proc.stdout.decode("utf-8",errors="replace"))
    except json.JSONDecodeError as exc: raise ProcessorSandboxError(proc.stderr.decode("utf-8",errors="replace")[:300]) from exc
    if not response.get("ok"): raise ProcessorSandboxError(f"{response.get('error')}: {response.get('message')}")
    result=response.get("result")
    if not isinstance(result,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in result.items()): raise ProcessorSandboxError("invalid processor output")
    return result

def write_outputs(output_dir: Path, files: dict[str,str]) -> None:
    root=output_dir.resolve(); root.mkdir(parents=True,exist_ok=True)
    for name,content in files.items():
        rel=Path(name)
        if rel.is_absolute() or ".." in rel.parts: raise ProcessorSandboxError(f"processor output escapes target: {name}")
        target=(root/rel).resolve()
        try: target.relative_to(root)
        except ValueError as exc: raise ProcessorSandboxError(f"processor output escapes target: {name}") from exc
        target.parent.mkdir(parents=True,exist_ok=True); target.write_text(content,encoding="utf-8")
