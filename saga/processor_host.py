from __future__ import annotations
"""Restricted annotation-processor worker.

Safe processors define ``process(metadata)`` and return ``{relative_path: text}``.
They run in the same OS-isolated host model as plugins.  The legacy
``process(metadata, output_dir)`` form is available only behind the explicit
``--unsafe-processor`` CLI flag.
"""
import ast
import builtins as _builtins
import json, sys
from types import MappingProxyType



class _ProcessorPolicy(ast.NodeVisitor):
    def visit_Import(self, node): raise ValueError("imports are not allowed in isolated processors")
    def visit_ImportFrom(self, node): raise ValueError("imports are not allowed in isolated processors")
    def visit_Attribute(self, node):
        if node.attr.startswith("__"): raise ValueError("dunder attribute access is not allowed in isolated processors")
        self.generic_visit(node)
    def visit_Name(self, node):
        if node.id.startswith("__") and node.id not in {"__name__"}: raise ValueError("dunder names are not allowed in isolated processors")
        self.generic_visit(node)

def _safe_builtins():
    names = (
        "abs","all","any","bool","dict","enumerate","filter","int","isinstance",
        "len","list","map","max","min","range","reversed","set","sorted","str",
        "sum","tuple","zip","Exception","ValueError","TypeError",
    )
    return {n:getattr(_builtins,n) for n in names}

def main() -> int:
    try:
        req=json.loads(sys.stdin.buffer.read().decode("utf-8"))
        source=req["source"]; metadata=req["metadata"]
        filename=req.get("filename","<processor>")
        tree=ast.parse(source,filename=filename,mode="exec"); _ProcessorPolicy().visit(tree)
        glb={"__builtins__":MappingProxyType(_safe_builtins()),"__name__":"saga_isolated_processor"}
        exec(compile(tree,filename,"exec",dont_inherit=True,optimize=2),glb,glb)
        fn=glb.get("process")
        if not callable(fn): raise ValueError("processor must define process(metadata)")
        result=fn(metadata)
        if not isinstance(result,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in result.items()):
            raise TypeError("safe processor must return {relative_path: text}")
        sys.stdout.write(json.dumps({"ok":True,"result":result},ensure_ascii=False,separators=(",",":")))
        return 0
    except BaseException as exc:
        sys.stdout.write(json.dumps({"ok":False,"error":type(exc).__name__,"message":str(exc)},ensure_ascii=False,separators=(",",":")))
        return 1
if __name__=="__main__": raise SystemExit(main())
