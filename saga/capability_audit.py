from __future__ import annotations
from pathlib import Path
from .api import compile_file
from . import ast_nodes as ast

MODULE_CAPABILITIES = {
    'io': {'filesystem'}, 'db': {'database'}, 'http': {'network'}, 'net': {'network'},
    'websocket': {'network'}, 'ui': {'ui'}, 'plugin': {'plugin'}, 'process': {'process'},
    'cloud': {'cloud','network'}, 'gpio': {'device'}, 'machine': {'device','network','realtime-control'}, 'spark': {'process'}, 'game': {'ui'}, 'image': {'filesystem'}, 'video': {'filesystem'},
}

def audit(file: str | Path) -> dict:
    loaded=compile_file(str(Path(file).expanduser())); modules=[]; caps=set()
    for st in loaded.program.statements:
        if isinstance(st, ast.UseStmt) and st.source_path is None:
            modules.append(st.module.lexeme); caps |= MODULE_CAPABILITIES.get(st.module.lexeme,set())
    return {'modules':sorted(set(modules)),'capabilities':sorted(caps),'policy':'deny-by-default','note':'actual paths/hosts remain runtime-granted; this is a static minimum category audit'}
