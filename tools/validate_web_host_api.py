#!/usr/bin/env python3
from __future__ import annotations
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; REL='0.38.0'
manifest=json.loads((ROOT/f'compatibility/web-host-api-{REL}.json').read_text())
names=[x for v in manifest['categories'].values() for x in v]
checker=(ROOT/'implementations/go/cmd/saga-go/checker.go').read_text();a=checker.index('if t.Name == "module:web"');b=checker.index('if t.Name == "module:db"',a);cb=checker[a:b]
kernel=(ROOT/'selfhost/sh3/kernel.saga').read_text();native=(ROOT/'implementations/go/cmd/saga-go/platform_expansion.go').read_text();js=(ROOT/'implementations/go/cmd/saga-go/web_runtime/sh3vm-browser.js').read_text()
checks={
 'manifest_count_101':len(names)==101 and len(set(names))==101 and manifest['api_count']==101,
 'checker_all_101':all(f'"{n}"' in cb for n in names),
 'canonical_sh3_all_101':all(f'web.{n}' in kernel for n in names),
 'native_reference_fail_closed_surface':all(f'"{n}"' in native for n in names),
 'browser_vm_dom_host':'dom.on_event' in js and 'dom.set_style' in js and 'dom.rect' in js,
 'browser_vm_storage_host':"storage.session_" in js and "cookie." in js and "localStorage" in js and "sessionStorage" in js,
 'browser_vm_navigation_host':'nav.push_state' in js and 'nav.reload' in js,
 'browser_vm_timer_host':'timer.set_timeout' in js and 'timer.animation_frame' in js,
 'browser_vm_network_host':'net.fetch' in js and 'ws.open' in js,
 'browser_vm_canvas_host':'canvas.fill_rect' in js and 'canvas.data_url' in js,
 'browser_vm_media_device_host':'media.play' in js and 'device.user_agent' in js,
 'browser_vm_permissioned_host':"clipboard." in js and "geo." in js and "fullscreen." in js,
}
missing_checker=[n for n in names if f'"{n}"' not in cb]
missing_kernel=[n for n in names if f'web.{n}' not in kernel]
report={'schema':1,'release':REL,'api_count':len(names),'checks':checks,'missing_checker':missing_checker,'missing_kernel':missing_kernel,'pass':all(checks.values()) and not missing_checker and not missing_kernel}
out=ROOT/f'validation/web-host-api-{REL}.json';out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));raise SystemExit(0 if report['pass'] else 1)
