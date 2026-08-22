#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; REL='0.38.0'
m=json.loads((ROOT/f'compatibility/app-action-api-{REL}.json').read_text())
apis=m['source_apis']; ops=[x for xs in m['categories'].values() for x in xs]
checker=(ROOT/'implementations/go/cmd/saga-go/checker.go').read_text()
a=checker.index('if t.Name == "module:app"'); b=checker.index('if t.Name == "module:web"',a); cb=checker[a:b]
kernel=(ROOT/'selfhost/sh3/kernel.saga').read_text()
js=(ROOT/'implementations/go/cmd/saga-go/web_runtime/sh3vm-browser.js').read_text()
native=(ROOT/'implementations/go/cmd/saga-go/platform_expansion.go').read_text()
checks={
 'source_api_unique':len(apis)==len(set(apis))==10,
 'checker_all':all(f'"{x}"' in cb for x in apis),
 'canonical_sh3_all':all(f'app.{x}' in kernel for x in apis),
 'browser_protocol':all(x in js for x in ('app.invoke','app.invoke_async','app.cancel','app.on','app.off')),
 'browser_operation_manifest':all(x in js for x in ops),
 'native_protocol':all(f'"{x}"' in native for x in ('host','capability','capabilities','operation_supported','operations','invoke','invoke_async','cancel','on','off')),
 'no_browser_eval_escape_hatch':'app.eval' not in js and 'eval_js' not in js,
}
report={'schema':1,'release':REL,'source_api_count':len(apis),'browser_operation_count':len(ops),'checks':checks,'pass':all(checks.values())}
out=ROOT/f'validation/app-action-api-{REL}.json';out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));raise SystemExit(0 if report['pass'] else 1)
