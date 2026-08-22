#!/usr/bin/env python3
from __future__ import annotations
import json, os, socket, subprocess, tempfile, time, urllib.request
from pathlib import Path
import websocket

ROOT=Path(__file__).resolve().parents[1]
REL='0.38.0'

def freeport():
    s=socket.socket();s.bind(('127.0.0.1',0));p=s.getsockname()[1];s.close();return p

def main():
    chromium=os.environ.get('SAGA_CHROMIUM') or 'chromium'
    xvfb=os.environ.get('SAGA_XVFB_RUN') or 'xvfb-run'
    js=(ROOT/'implementations/go/cmd/saga-go/web_runtime/sh3vm-browser.js').read_text()
    kernel=(ROOT/'implementations/go/cmd/saga-go/web_runtime/kernel.sbc').read_text()
    src=(ROOT/'examples/web/chromium_runtime_smoke.saga').read_text()
    port=freeport(); profile=tempfile.mkdtemp(prefix='saga-chromium-')
    env={**os.environ,'NO_PROXY':'127.0.0.1,localhost','no_proxy':'127.0.0.1,localhost'}
    proc=subprocess.Popen([xvfb,'-a',chromium,'--no-sandbox','--disable-gpu','--disable-dev-shm-usage','--disable-background-networking','--disable-sync','--metrics-recording-only','--no-first-run','--disable-default-apps','--remote-allow-origins=*',f'--remote-debugging-port={port}',f'--user-data-dir={profile}','about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,env=env)
    evidence={'schema':1,'release':REL,'browser':'','execution':'real Chromium Blink/V8 via DevTools Protocol','origin':'about:blank','managed_url_policy_bypassed':False,'checks':{},'pass':False}
    ws=None
    try:
        pages=[]
        for _ in range(100):
            try:
                pages=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/list',timeout=1))
                if pages:break
            except Exception:pass
            time.sleep(.1)
        if not pages:raise RuntimeError('Chromium DevTools endpoint unavailable')
        page=next(x for x in pages if x.get('type')=='page')
        ws=websocket.create_connection(page['webSocketDebuggerUrl'],origin='http://127.0.0.1',timeout=8)
        seq=0
        def cmd(method,params=None):
            nonlocal seq
            seq+=1;i=seq;ws.send(json.dumps({'id':i,'method':method,'params':params or {}}))
            while True:
                m=json.loads(ws.recv())
                if m.get('id')==i:
                    if 'error' in m:raise RuntimeError(m['error'])
                    return m.get('result',{})
        def ev(expr):
            r=cmd('Runtime.evaluate',{'expression':expr,'returnByValue':True})['result']
            if r.get('subtype')=='error':raise RuntimeError(r)
            return r.get('value')
        cmd('Runtime.enable');cmd('Page.enable')
        ev("document.body.innerHTML='<main id=\"saga-root\"></main><pre id=\"saga-output\"></pre>';true")
        ev('(0,eval)('+json.dumps(js)+'); true')
        files={'/app/main.saga':src}
        boot=f"""(()=>{{const kernel={json.dumps(kernel)};const files={json.dumps(files)};globalThis.__eventLog=[];globalThis.__sagaOut='';function run(extra){{globalThis.__sagaOut='';return runSagaSH3(kernel,['run','/app/main.saga'].concat(extra||[]),files,s=>{{globalThis.__sagaOut+=s;}});}}globalThis.__sagaDispatch=(args)=>{{globalThis.__eventLog.push(args);run(args||[]);}};globalThis.__initialResult=run([]);return {{code:globalThis.__initialResult.code,out:globalThis.__sagaOut}};}})()"""
        init=ev(boot)
        if init['code']!=0:raise RuntimeError('Saga initial execution failed: '+repr(init))
        state=ev("(()=>({title:document.title,api:document.getElementById('panel').getAttribute('data-api'),ready:document.getElementById('panel').classList.contains('ready'),display:getComputedStyle(document.getElementById('panel')).display,value:document.getElementById('name').value,checked:document.getElementById('check').checked,selected:document.getElementById('sel').selectedIndex,canvas:document.getElementById('cv').toDataURL('image/png').startsWith('data:image/png;base64,'),href:location.href}))()")
        ev("document.getElementById('btn').click(); window.dispatchEvent(new Event('resize')); true")
        ev("(()=>{const e=document.getElementById('name');e.value='Chromium';e.dispatchEvent(new Event('input',{bubbles:true}));return true})()")
        for _ in range(100):
            log=ev('globalThis.__eventLog') or []; kinds=[x[0] for x in log]
            if all(k in kinds for k in ('click','input','timeout','fetch','app','app_event')):break
            time.sleep(.05)
        out=ev('globalThis.__sagaOut');log=ev('globalThis.__eventLog') or []
        lines=[x for x in out.strip().splitlines() if x]
        version=json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json/version',timeout=2))['Browser']
        fetch_events=[x for x in log if x and x[0]=='fetch']
        fetch_body=fetch_events[-1][5] if fetch_events and len(fetch_events[-1])>5 else ''
        evidence['browser']=version
        evidence['checks']={
            'edition_2027_browser_execution':init['code']==0,
            'dom_title':state['title']=='Saga Chromium PASS',
            'dom_attribute':state['api']=='expanded',
            'class_and_style':bool(state['ready']) and state['display']=='block',
            'form_value':state['value']=='Saga',
            'checkbox':bool(state['checked']),
            'select_index':state['selected']==1,
            'canvas_real_png':bool(state['canvas']),
            'click_event':'click' in [x[0] for x in log],
            'input_event':'input' in [x[0] for x in log],
            'timer_event':'timeout' in [x[0] for x in log],
            'fetch_event':'fetch' in [x[0] for x in log] and fetch_body=='probe-ok',
            'browser_dom_capability':len(lines)>=1 and lines[0]=='true',
            'dom_capability':len(lines)>=2 and lines[1]=='true',
            'fetch_capability':len(lines)>=3 and lines[2]=='true',
            'storage_fail_closed_on_opaque_origin':len(lines)>=4 and lines[3]=='false',
            'universal_app_host':len(lines)>=5 and lines[4]=='browser',
            'universal_app_browser_capability':len(lines)>=6 and lines[5]=='true',
            'universal_app_operation_manifest':len(lines)>=7 and lines[6]=='true',
            'universal_app_sync_invoke':len(lines)>=9 and lines[7]=='true' and lines[8]=='true',
            'universal_app_async_event':'app' in [x[0] for x in log],
            'universal_app_lifecycle_event':'app_event' in [x[0] for x in log],
        }
        evidence['event_kinds']=[x[0] for x in log]
        evidence['fetch_body']=fetch_body
        evidence['capability_output']=lines
        evidence['pass']=all(evidence['checks'].values()) and version.startswith('Chrome/')
        # The validation host has an enterprise URLBlocklist=* policy. We deliberately do not alter it.
        policy=Path('/etc/chromium/policies/managed/000_policy_merge.json')
        if policy.exists():
            try:evidence['host_managed_url_blocklist']=json.loads(policy.read_text()).get('URLBlocklist',[])
            except Exception:pass
    finally:
        if ws:
            try:ws.close()
            except Exception:pass
        try:proc.terminate();proc.wait(timeout=5)
        except Exception:
            try:proc.kill()
            except Exception:pass
    out=ROOT/f'validation/chromium-web-{REL}.json';out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(evidence,ensure_ascii=False,indent=2))
    return 0 if evidence['pass'] else 1
if __name__=='__main__':raise SystemExit(main())
