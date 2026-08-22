from __future__ import annotations
import json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def case_names(text:str, indent_tabs:int|None=None)->set[str]:
    out=set()
    for line in text.splitlines():
        if indent_tabs is not None:
            prefix='\t'*indent_tabs+'case '
            if not line.startswith(prefix):
                continue
        elif not line.lstrip().startswith('case '):
            continue
        out.update(re.findall(r'"([a-zA-Z0-9_]+)"', line))
    return out

checker=(ROOT/'implementations/go/cmd/saga-go/checker.go').read_text()
start=checker.index('if t.Name == "module:game"')
end=checker.index('return TAny, c.err(v.Tok, "SAGA-T106", "unknown game member "+v.Name)',start)
checked=case_names(checker[start:end],2)

api=(ROOT/'implementations/go/cmd/saga-go/game_api.go').read_text()
start=api.index('func (i *Interpreter) callGameExtended')
extended=case_names(api[start:],1)
platform=(ROOT/'implementations/go/cmd/saga-go/platform_expansion.go').read_text()
pstart=platform.index('if module == "game"')
pexpanded=case_names(platform[pstart:],2)

native=(ROOT/'implementations/go/cmd/saga-go/native_modules.go').read_text()
start=native.index('case "game":')
end=native.index('if v, handled, err := i.callGameExtended',start)
terminal=case_names(native[start:end],2)
runtime=terminal|extended|pexpanded

manifest=json.loads((ROOT/'compatibility/native-game-api-0.38.0.json').read_text())
manifest_names=set(manifest['profiles']['desktop_game_1_0_rc1']['functions'])

errors=[]
if checked != runtime:
    errors.append(f'checker/runtime mismatch missing_runtime={sorted(checked-runtime)} extra_runtime={sorted(runtime-checked)}')
if checked != manifest_names:
    errors.append(f'checker/manifest mismatch missing_manifest={sorted(checked-manifest_names)} extra_manifest={sorted(manifest_names-checked)}')
if manifest['api_count'] != len(checked):
    errors.append(f"manifest api_count={manifest['api_count']} actual={len(checked)}")
report={'schema':1,'release':'0.38.0','api_count':len(checked),'checker_runtime_aligned':checked==runtime,'checker_manifest_aligned':checked==manifest_names,'errors':errors,'pass':not errors}
out=ROOT/'validation/native-game-api-0.38.0.json';out.write_text(json.dumps(report,indent=2)+'\n')
if errors:
    raise SystemExit('\n'.join(errors))
print(f'PASS: Native game API checker/runtime/manifest aligned ({len(checked)} functions)')
