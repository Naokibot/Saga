/* Saga SH-3 browser bootstrap VM 0.23.
 * Language-neutral port of bootstrap/sh3/sh3vm.c. Saga syntax/type/runtime
 * policy remains in kernel.saga/kernel.sbc, not in this VM.
 */
(function (root) {
  'use strict';
  const enc = new TextEncoder();
  const dec = new TextDecoder('utf-8', {fatal:false});
  const UNIT = Object.freeze({k:'unit'});
  const APP_OPERATIONS = Object.freeze(["system.snapshot", "crypto.random_uuid", "device.gamepads", "device.vibrate", "device.connection", "device.screen", "notification.permission", "notification.request", "notification.show", "share", "media.enumerate_devices", "media.request_user_media", "media.stop", "file.open_text", "file.save_text", "file.pick_directory", "bluetooth.request_device", "usb.request_device", "serial.request_port", "hid.request_device", "midi.request_access", "nfc.scan", "nfc.write", "contacts.select", "wake_lock.request", "wake_lock.release", "orientation.lock", "orientation.unlock", "keyboard.lock", "keyboard.unlock", "pointer_lock.request", "pointer_lock.exit", "badge.set", "badge.clear", "screen.get_details", "permission.query", "webgpu.request_adapter", "webrtc.create_peer", "webrtc.add_media_stream", "webrtc.create_data_channel", "webrtc.create_offer", "webrtc.set_local_description", "webrtc.set_remote_description", "webrtc.add_ice_candidate", "webrtc.close", "webtransport.open", "webtransport.close", "payment.request", "credentials.get", "eye_dropper.open", "xr.request_session", "idle.request", "push.subscribe", "speech.speak", "speech.cancel"]);
  const vi = x => ({k:'int', v:BigInt(x)});
  const vb = x => ({k:'bool', v:!!x});
  const vt = x => ({k:'text', v:String(x)});
  const vl = x => ({k:'list', v:x || []});
  const clone = v => v && v.k === 'list' ? vl(v.v.map(clone)) : (v && v.k === 'text' ? vt(v.v) : v);
  const bytes = s => enc.encode(String(s));
  const fromBytes = b => dec.decode(b);
  const safeFeature = fn => { try { return !!fn(); } catch (_) { return false; } };
  function unhex(h) {
    if (h === '-') return '';
    if (!h || h.length % 2) throw new Error('invalid hex text');
    const out = new Uint8Array(h.length / 2);
    for (let i=0;i<h.length;i+=2) {
      const n = Number.parseInt(h.slice(i,i+2),16);
      if (!Number.isFinite(n)) throw new Error('invalid hex text');
      out[i/2] = n;
    }
    return fromBytes(out);
  }
  function textOf(v) {
    if (!v || v.k === 'unit') return 'unit';
    if (v.k === 'text') return v.v;
    if (v.k === 'int') return v.v.toString();
    if (v.k === 'bool') return v.v ? 'true' : 'false';
    if (v.k === 'list') return '[' + v.v.map(textOf).join(', ') + ']';
    return '?';
  }
  function truth(v) {
    if (!v || v.k === 'unit') return false;
    if (v.k === 'bool') return v.v;
    if (v.k === 'int') return v.v !== 0n;
    if (v.k === 'text') return bytes(v.v).length !== 0;
    if (v.k === 'list') return v.v.length !== 0;
    return false;
  }
  function parseProgram(text) {
    const p = {funcs:new Map(), entry:'', globals:[]};
    let cur = null;
    for (const raw of String(text).split(/\r?\n/)) {
      const line = raw.trim();
      if (!line || line.startsWith('#')) continue;
      const parts = line.split(/[ \t]+/);
      const [op,a,b,c] = parts;
      if (op === 'SH3BC1') continue;
      if (op === 'GLOBALS') { p.globals = Array(Number(a)).fill(UNIT); continue; }
      if (op === 'ENTRY') { p.entry = unhex(a); continue; }
      if (op === 'FUNC') { cur = {name:unhex(a), argc:Number(b), locals:Number(c), code:[], labels:new Map()}; p.funcs.set(cur.name,cur); continue; }
      if (op === 'END') { cur = null; continue; }
      if (!cur) throw new Error('instruction outside FUNC');
      if (op === 'LABEL') { cur.labels.set(a,cur.code.length); continue; }
      cur.code.push({op,a,b});
    }
    if (!p.entry) throw new Error('missing ENTRY');
    return p;
  }
  function byteSubstring(s,a,b) {
    const q=bytes(s); a=Math.max(0,Math.min(Number(a),q.length)); b=Math.max(a,Math.min(Number(b),q.length)); return fromBytes(q.slice(a,b));
  }
  function byteFind(s, needle) {
    const a=bytes(s), b=bytes(needle); if (!b.length) return 0n;
    outer: for(let i=0;i+b.length<=a.length;i++){ for(let j=0;j<b.length;j++) if(a[i+j]!==b[j]) continue outer; return BigInt(i); }
    return -1n;
  }
  function byteStarts(s,p){const a=bytes(s),b=bytes(p);if(b.length>a.length)return false;for(let i=0;i<b.length;i++)if(a[i]!==b[i])return false;return true;}
  function byteEnds(s,p){const a=bytes(s),b=bytes(p);if(b.length>a.length)return false;const o=a.length-b.length;for(let i=0;i<b.length;i++)if(a[o+i]!==b[i])return false;return true;}
  class VMExit extends Error { constructor(code){super('VM exit '+code);this.code=Number(code);} }
  class SagaSH3VM {
    constructor(programText, options={}) {
      this.program=parseProgram(programText);
      this.args=(options.args||[]).map(String);
      this.files=Object.assign(Object.create(null), options.files||{});
      this.stdout=options.stdout || (s => { if (root.document) { const e=root.document.getElementById('saga-output'); if(e)e.textContent += s; } else if(root.console) root.console.log(s.replace(/\n$/,'')); });
      this.maxDepth=options.maxDepth || 4096;
      this.externalHostCall=options.hostCall || null;
      this.webState={nextId:1,timers:new Map(),fetches:new Map(),sockets:new Map(),appAsync:new Map(),appEvents:new Map(),mediaStreams:new Map(),wakeLocks:new Map(),peers:new Map(),transports:new Map(),gpuAdapters:new Map()};
    }
    dispatchWeb(kind, action, extra=[]) {
      if(typeof root.__sagaDispatch==='function') root.__sagaDispatch([String(kind),String(action||'')].concat(extra.map(x=>String(x==null?'':x))));
    }
    bindEvent(el, eventName, action) {
      if(!el.__sagaHandlers) Object.defineProperty(el,'__sagaHandlers',{value:Object.create(null),configurable:true});
      const key=String(eventName)+'|'+String(action);
      const prev=el.__sagaHandlers[key]; if(prev){if(typeof el.removeEventListener==='function')el.removeEventListener(eventName,prev);else if(el['on'+eventName]===prev)el['on'+eventName]=null;}
      const fn=(e)=>{
        if(eventName==='submit' && e && typeof e.preventDefault==='function')e.preventDefault();
        const target=(e&&e.target)||el;
        this.dispatchWeb(eventName,action,[el.id||'',e&&e.key||'',target&&target.value==null?'':target.value,target&&target.checked?'true':'false',e&&Number.isFinite(e.clientX)?e.clientX:'',e&&Number.isFinite(e.clientY)?e.clientY:'',e&&Number.isFinite(e.button)?e.button:'']);
      };
      el.__sagaHandlers[key]=fn; if(typeof el.addEventListener==='function')el.addEventListener(eventName,fn);else el['on'+eventName]=fn;
    }
    appCapability(name) {
      const nav=root.navigator||{}, doc=root.document||null;
      const caps={
        browser:true,dom:!!doc,storage:safeFeature(()=>root.localStorage),session:safeFeature(()=>root.sessionStorage),cookie:!!doc,navigation:!!root.location,timer:typeof root.setTimeout==='function',fetch:typeof root.fetch==='function',websocket:typeof root.WebSocket==='function',canvas:!!doc,media:!!nav.mediaDevices,clipboard:!!nav.clipboard,geolocation:!!nav.geolocation,fullscreen:!!(doc&&doc.documentElement&&doc.documentElement.requestFullscreen),notifications:typeof root.Notification==='function',share:typeof nav.share==='function',files:typeof root.showOpenFilePicker==='function'||typeof root.showSaveFilePicker==='function',bluetooth:!!nav.bluetooth,usb:!!nav.usb,serial:!!nav.serial,hid:!!nav.hid,midi:typeof nav.requestMIDIAccess==='function',nfc:typeof root.NDEFReader==='function',webrtc:typeof root.RTCPeerConnection==='function',webgpu:!!nav.gpu,webcodecs:typeof root.VideoDecoder==='function'||typeof root.AudioDecoder==='function',webtransport:typeof root.WebTransport==='function',payments:typeof root.PaymentRequest==='function',credentials:!!nav.credentials,push:safeFeature(()=>root.PushManager&&nav.serviceWorker),wake_lock:!!nav.wakeLock,contacts:!!nav.contacts,xr:!!nav.xr,speech:!!root.speechSynthesis,vibration:typeof nav.vibrate==='function',gamepad:typeof nav.getGamepads==='function',orientation:!!(root.screen&&root.screen.orientation),keyboard:!!nav.keyboard,pointer_lock:!!(doc&&doc.body&&doc.body.requestPointerLock),badge:typeof nav.setAppBadge==='function',screen_details:typeof root.getScreenDetails==='function',idle_detection:typeof root.IdleDetector==='function',permissions:!!nav.permissions
      };
      return !!caps[String(name||'')];
    }
    appCapabilities() {
      const names=['browser','dom','storage','session','cookie','navigation','timer','fetch','websocket','canvas','media','clipboard','geolocation','fullscreen','notifications','share','files','bluetooth','usb','serial','hid','midi','nfc','webrtc','webgpu','webcodecs','webtransport','payments','credentials','push','wake_lock','contacts','xr','speech','vibration','gamepad','orientation','keyboard','pointer_lock','badge','screen_details','idle_detection','permissions'];
      return names.filter(n=>this.appCapability(n));
    }
    appPayload(text) { if(!text)return {}; const v=JSON.parse(String(text)); if(v===null||typeof v!=='object'||Array.isArray(v))throw Error('app payload must be a JSON object'); return v; }
    appJSON(value) { return JSON.stringify(value===undefined?null:value); }
    appInvoke(operation,payloadText) {
      const op=String(operation||''), p=this.appPayload(payloadText), nav=root.navigator||{}, doc=root.document||null;
      if(op==='system.snapshot')return this.appJSON({host:'browser',online:nav.onLine!==false,language:nav.language||'',user_agent:nav.userAgent||'',viewport_width:root.innerWidth||0,viewport_height:root.innerHeight||0,pixel_ratio:root.devicePixelRatio||1,visibility:doc?doc.visibilityState:'unknown',secure_context:!!root.isSecureContext});
      if(op==='crypto.random_uuid'){if(root.crypto&&typeof root.crypto.randomUUID==='function')return root.crypto.randomUUID();if(root.crypto&&typeof root.crypto.getRandomValues==='function'){const b=new Uint8Array(16);root.crypto.getRandomValues(b);b[6]=(b[6]&15)|64;b[8]=(b[8]&63)|128;const h=Array.from(b,x=>x.toString(16).padStart(2,'0')).join('');return h.slice(0,8)+'-'+h.slice(8,12)+'-'+h.slice(12,16)+'-'+h.slice(16,20)+'-'+h.slice(20);}throw Error('cryptographic random source unavailable');}
      if(op==='device.gamepads'){if(!this.appCapability('gamepad'))throw Error('gamepad unavailable');return this.appJSON(Array.from(nav.getGamepads()||[]).filter(Boolean).map(g=>({id:g.id,index:g.index,connected:g.connected,mapping:g.mapping,timestamp:g.timestamp,axes:Array.from(g.axes||[]),buttons:Array.from(g.buttons||[]).map(b=>({pressed:b.pressed,touched:b.touched,value:b.value}))})));}
      if(op==='device.vibrate'){if(!this.appCapability('vibration'))throw Error('vibration unavailable');return this.appJSON({accepted:!!nav.vibrate(p.pattern==null?(p.ms||0):p.pattern)});}
      if(op==='device.connection'){const c=nav.connection||nav.mozConnection||nav.webkitConnection;if(!c)throw Error('network information unavailable');return this.appJSON({effective_type:c.effectiveType||'',downlink:c.downlink||0,rtt:c.rtt||0,save_data:!!c.saveData,type:c.type||''});}
      if(op==='device.screen'){const sc=root.screen||{};return this.appJSON({width:sc.width||0,height:sc.height||0,avail_width:sc.availWidth||0,avail_height:sc.availHeight||0,color_depth:sc.colorDepth||0,pixel_depth:sc.pixelDepth||0,orientation:sc.orientation?sc.orientation.type||'':''});}
      if(op==='notification.permission'){return String(root.Notification?root.Notification.permission:'unsupported');}
      if(op==='media.stop'){const id=Number(p.id||0),stream=this.webState.mediaStreams.get(id);if(!stream)throw Error('media stream handle not found');for(const tr of stream.getTracks())tr.stop();this.webState.mediaStreams.delete(id);return this.appJSON({stopped:true,id});}
      if(op==='webrtc.create_peer'){if(!this.appCapability('webrtc'))throw Error('WebRTC unavailable');const id=this.webState.nextId++;const pc=new root.RTCPeerConnection(p.config||{});this.webState.peers.set(id,pc);return this.appJSON({id});}
      if(op==='webrtc.add_media_stream'){const id=Number(p.id||0),sid=Number(p.stream_id||0),pc=this.webState.peers.get(id),stream=this.webState.mediaStreams.get(sid);if(!pc)throw Error('peer handle not found');if(!stream)throw Error('media stream handle not found');let count=0;for(const tr of stream.getTracks()){pc.addTrack(tr,stream);count++;}return this.appJSON({added_tracks:count,id,stream_id:sid});}
      if(op==='webrtc.create_data_channel'){const id=Number(p.id||0),pc=this.webState.peers.get(id);if(!pc)throw Error('peer handle not found');const dc=pc.createDataChannel(String(p.label||'saga'),p.options||{});return this.appJSON({label:dc.label||String(p.label||'saga'),ready_state:dc.readyState||'connecting'});}
      if(op==='webrtc.close'){const id=Number(p.id||0),pc=this.webState.peers.get(id);if(!pc)throw Error('peer handle not found');pc.close();this.webState.peers.delete(id);return this.appJSON({closed:true,id});}
      if(op==='webtransport.close'){const id=Number(p.id||0),tr=this.webState.transports.get(id);if(!tr)throw Error('WebTransport handle not found');tr.close({closeCode:Number(p.code||0),reason:String(p.reason||'')});this.webState.transports.delete(id);return this.appJSON({closed:true,id});}
      if(op==='wake_lock.release'){const id=Number(p.id||0),lock=this.webState.wakeLocks.get(id);if(!lock)throw Error('wake lock handle not found');const q=lock.release();this.webState.wakeLocks.delete(id);if(q&&q.catch)q.catch(()=>{});return this.appJSON({released:true,id});}
      if(op==='orientation.unlock'){if(!this.appCapability('orientation')||typeof root.screen.orientation.unlock!=='function')throw Error('orientation unlock unavailable');root.screen.orientation.unlock();return this.appJSON({unlocked:true});}
      if(op==='keyboard.unlock'){if(!this.appCapability('keyboard')||typeof nav.keyboard.unlock!=='function')throw Error('keyboard unlock unavailable');nav.keyboard.unlock();return this.appJSON({unlocked:true});}
      if(op==='pointer_lock.request'){if(!doc)throw Error('pointer lock unavailable');const el=doc.getElementById(String(p.id||''));if(!el||!el.requestPointerLock)throw Error('pointer lock target unavailable');el.requestPointerLock();return this.appJSON({requested:true});}
      if(op==='pointer_lock.exit'){if(!doc||!doc.exitPointerLock)throw Error('pointer lock unavailable');doc.exitPointerLock();return this.appJSON({exited:true});}
      if(op==='speech.speak'){if(!this.appCapability('speech'))throw Error('speech synthesis unavailable');const u=new SpeechSynthesisUtterance(String(p.text||''));if(p.lang)u.lang=String(p.lang);if(p.rate!=null)u.rate=Number(p.rate);if(p.pitch!=null)u.pitch=Number(p.pitch);if(p.volume!=null)u.volume=Number(p.volume);root.speechSynthesis.speak(u);return this.appJSON({queued:true});}
      if(op==='speech.cancel'){if(!this.appCapability('speech'))throw Error('speech synthesis unavailable');root.speechSynthesis.cancel();return this.appJSON({cancelled:true});}
      throw Error('app operation requires async host or is unsupported: '+op);
    }
    appAsyncResult(id,operation,action,ok,value) {
      const state=this.webState.appAsync.get(id); if(!state||state.cancelled)return;
      this.webState.appAsync.delete(id); this.dispatchWeb('app',action,[operation,String(id),ok?'true':'false',this.appJSON(value)]);
    }
    appInvokeAsync(operation,payloadText,action) {
      const op=String(operation||''), p=this.appPayload(payloadText), id=this.webState.nextId++, nav=root.navigator||{}, doc=root.document||null;
      const state={cancelled:false,abort:null};this.webState.appAsync.set(id,state);
      const done=(ok,v)=>this.appAsyncResult(id,op,String(action||''),ok,v); const fail=e=>done(false,{error:String(e&&e.message||e)});
      let promise;
      try {
        if(op==='permission.query'){if(!nav.permissions)throw Error('permissions unavailable');promise=nav.permissions.query({name:String(p.name||'')}).then(x=>({state:x.state}));}
        else if(op==='notification.request'){if(!root.Notification)throw Error('notifications unavailable');promise=root.Notification.requestPermission().then(x=>({permission:x}));}
        else if(op==='notification.show'){if(!root.Notification||root.Notification.permission!=='granted')throw Error('notification permission not granted');const n=new root.Notification(String(p.title||''),p.options||{});promise=Promise.resolve({shown:true});}
        else if(op==='share'){if(!nav.share)throw Error('share unavailable');promise=nav.share(p).then(()=>({shared:true}));}
        else if(op==='media.enumerate_devices'){if(!nav.mediaDevices)throw Error('media devices unavailable');promise=nav.mediaDevices.enumerateDevices().then(xs=>xs.map(x=>({device_id:x.deviceId,group_id:x.groupId,kind:x.kind,label:x.label})));}
        else if(op==='media.request_user_media'){if(!nav.mediaDevices)throw Error('user media unavailable');promise=nav.mediaDevices.getUserMedia({audio:p.audio==null?false:p.audio,video:p.video==null?false:p.video}).then(stream=>{const sid=this.webState.nextId++;this.webState.mediaStreams.set(sid,stream);return {id:sid,tracks:stream.getTracks().map(t=>({kind:t.kind,label:t.label,enabled:t.enabled,muted:t.muted,ready_state:t.readyState}))};});}
        else if(op==='file.open_text'){if(!root.showOpenFilePicker)throw Error('file picker unavailable');promise=root.showOpenFilePicker(p.options||{}).then(async hs=>{const f=await hs[0].getFile();return {name:f.name,size:f.size,type:f.type,text:await f.text()};});}
        else if(op==='file.save_text'){if(!root.showSaveFilePicker)throw Error('save file picker unavailable');promise=root.showSaveFilePicker(p.options||{}).then(async h=>{const w=await h.createWritable();await w.write(String(p.text||''));await w.close();return {saved:true,name:h.name||''};});}
        else if(op==='file.pick_directory'){if(!root.showDirectoryPicker)throw Error('directory picker unavailable');promise=root.showDirectoryPicker(p.options||{}).then(h=>({name:h.name||'',kind:h.kind||'directory'}));}
        else if(op==='bluetooth.request_device'){if(!nav.bluetooth)throw Error('Web Bluetooth unavailable');promise=nav.bluetooth.requestDevice(p.options||{acceptAllDevices:true}).then(d=>({id:d.id,name:d.name||''}));}
        else if(op==='usb.request_device'){if(!nav.usb)throw Error('WebUSB unavailable');promise=nav.usb.requestDevice(p.options||{filters:[]}).then(d=>({vendor_id:d.vendorId,product_id:d.productId,product_name:d.productName||'',manufacturer_name:d.manufacturerName||'',serial_number:d.serialNumber||''}));}
        else if(op==='serial.request_port'){if(!nav.serial)throw Error('Web Serial unavailable');promise=nav.serial.requestPort(p.options||{}).then(()=>({selected:true}));}
        else if(op==='hid.request_device'){if(!nav.hid)throw Error('WebHID unavailable');promise=nav.hid.requestDevice(p.options||{filters:[]}).then(ds=>ds.map(d=>({vendor_id:d.vendorId,product_id:d.productId,product_name:d.productName||''})));}
        else if(op==='midi.request_access'){if(!nav.requestMIDIAccess)throw Error('Web MIDI unavailable');promise=nav.requestMIDIAccess(p.options||{}).then(a=>({inputs:a.inputs.size,outputs:a.outputs.size,sysex_enabled:!!a.sysexEnabled}));}
        else if(op==='nfc.scan'){if(!root.NDEFReader)throw Error('Web NFC unavailable');const r=new root.NDEFReader();promise=r.scan().then(()=>({scanning:true}));}
        else if(op==='nfc.write'){if(!root.NDEFReader)throw Error('Web NFC unavailable');const r=new root.NDEFReader();promise=r.write(p.message==null?String(p.text||''):p.message).then(()=>({written:true}));}
        else if(op==='contacts.select'){if(!nav.contacts)throw Error('Contact Picker unavailable');promise=nav.contacts.select(p.properties||['name','email','tel'],p.options||{multiple:false});}
        else if(op==='wake_lock.request'){if(!nav.wakeLock)throw Error('Wake Lock unavailable');promise=nav.wakeLock.request(String(p.type||'screen')).then(lock=>{const lid=this.webState.nextId++;this.webState.wakeLocks.set(lid,lock);return {id:lid,released:!!lock.released};});}
        else if(op==='orientation.lock'){if(!root.screen||!root.screen.orientation||!root.screen.orientation.lock)throw Error('orientation lock unavailable');promise=root.screen.orientation.lock(String(p.type||'portrait-primary')).then(()=>({locked:true}));}
        else if(op==='keyboard.lock'){if(!nav.keyboard||!nav.keyboard.lock)throw Error('keyboard lock unavailable');promise=nav.keyboard.lock(Array.isArray(p.keys)?p.keys:undefined).then(()=>({locked:true}));}
        else if(op==='badge.set'){if(!nav.setAppBadge)throw Error('app badge unavailable');promise=nav.setAppBadge(Number(p.value||0)).then(()=>({set:true}));}
        else if(op==='badge.clear'){if(!nav.clearAppBadge)throw Error('app badge unavailable');promise=nav.clearAppBadge().then(()=>({cleared:true}));}
        else if(op==='screen.get_details'){if(!root.getScreenDetails)throw Error('Window Management unavailable');promise=root.getScreenDetails().then(d=>({current:{left:d.currentScreen.left,top:d.currentScreen.top,width:d.currentScreen.width,height:d.currentScreen.height,label:d.currentScreen.label||''},screens:Array.from(d.screens||[]).map(x=>({left:x.left,top:x.top,width:x.width,height:x.height,label:x.label||''}))}));}
        else if(op==='webgpu.request_adapter'){if(!nav.gpu)throw Error('WebGPU unavailable');promise=nav.gpu.requestAdapter(p.options||{}).then(a=>{if(!a)throw Error('no WebGPU adapter');const aid=this.webState.nextId++;this.webState.gpuAdapters.set(aid,a);return {id:aid,features:Array.from(a.features||[])};});}
        else if(op==='webrtc.create_offer'){const pc=this.webState.peers.get(Number(p.id||0));if(!pc)throw Error('peer handle not found');promise=pc.createOffer(p.options||{}).then(o=>({type:o.type,sdp:o.sdp||''}));}
        else if(op==='webrtc.set_local_description'){const pc=this.webState.peers.get(Number(p.id||0));if(!pc)throw Error('peer handle not found');promise=pc.setLocalDescription({type:String(p.type||''),sdp:String(p.sdp||'')}).then(()=>({set:true}));}
        else if(op==='webrtc.set_remote_description'){const pc=this.webState.peers.get(Number(p.id||0));if(!pc)throw Error('peer handle not found');promise=pc.setRemoteDescription({type:String(p.type||''),sdp:String(p.sdp||'')}).then(()=>({set:true}));}
        else if(op==='webrtc.add_ice_candidate'){const pc=this.webState.peers.get(Number(p.id||0));if(!pc)throw Error('peer handle not found');promise=pc.addIceCandidate(p.candidate||null).then(()=>({added:true}));}
        else if(op==='webtransport.open'){if(!root.WebTransport)throw Error('WebTransport unavailable');const tr=new root.WebTransport(String(p.url||''),p.options||{});promise=tr.ready.then(()=>{const tid=this.webState.nextId++;this.webState.transports.set(tid,tr);return {id:tid,ready:true};});}
        else if(op==='payment.request'){if(!root.PaymentRequest)throw Error('Payment Request unavailable');const req=new root.PaymentRequest(p.method_data||[],p.details||{},p.options||{});promise=req.show().then(async r=>{const out={method_name:r.methodName,details:r.details,payer_name:r.payerName||'',payer_email:r.payerEmail||'',payer_phone:r.payerPhone||''};await r.complete(String(p.complete||'success'));return out;});}
        else if(op==='credentials.get'){if(!nav.credentials)throw Error('Credential Management unavailable');promise=nav.credentials.get(p.options||{}).then(c=>c?{id:c.id,type:c.type}:null);}
        else if(op==='eye_dropper.open'){if(!root.EyeDropper)throw Error('EyeDropper unavailable');promise=new root.EyeDropper().open().then(r=>({srgb_hex:r.sRGBHex}));}
        else if(op==='xr.request_session'){if(!nav.xr)throw Error('WebXR unavailable');promise=nav.xr.requestSession(String(p.mode||'inline'),p.options||{}).then(s=>({visibility_state:s.visibilityState||'visible'}));}
        else if(op==='idle.request'){if(!root.IdleDetector)throw Error('Idle Detection unavailable');promise=root.IdleDetector.requestPermission().then(x=>({permission:x}));}
        else if(op==='push.subscribe'){if(!nav.serviceWorker||!root.PushManager)throw Error('Push unavailable');promise=nav.serviceWorker.ready.then(r=>r.pushManager.subscribe(p.options||{userVisibleOnly:true})).then(s=>s.toJSON?s.toJSON():{endpoint:s.endpoint});}
        else throw Error('unknown async app operation '+op);
      } catch(e) { this.webState.appAsync.delete(id); throw e; }
      Promise.resolve(promise).then(v=>done(true,v)).catch(fail); return id;
    }
    appCancel(id) { const s=this.webState.appAsync.get(Number(id)); if(!s)return false;s.cancelled=true;if(s.abort&&typeof s.abort.abort==='function')s.abort.abort();this.webState.appAsync.delete(Number(id));return true; }
    appOn(eventName,action) {
      const event=String(eventName||''), id=this.webState.nextId++, target=['visibilitychange','fullscreenchange','pointerlockchange'].includes(event)?root.document:root;
      if(!target||typeof target.addEventListener!=='function')throw Error('event host unavailable');
      const fn=(e)=>{let data={type:event};if(event==='visibilitychange'&&root.document)data.visibility=root.document.visibilityState;if(event==='online'||event==='offline')data.online=(root.navigator||{}).onLine!==false;if(event==='resize'){data.width=root.innerWidth||0;data.height=root.innerHeight||0;}this.dispatchWeb('app_event',action,[event,String(id),this.appJSON(data)]);};
      target.addEventListener(event,fn);this.webState.appEvents.set(id,{target,event,fn});return id;
    }
    appOff(id) { const q=this.webState.appEvents.get(Number(id));if(!q)return false;q.target.removeEventListener(q.event,q.fn);this.webState.appEvents.delete(Number(id));return true; }
    hostCall(op,args) {
      if(this.externalHostCall)return this.externalHostCall(op,args,{vi,vb,vt,vl,UNIT,clone,textOf});
      const vals=args.map(textOf);
      if(op.startsWith('app.')){
        if(op==='app.host')return vt('browser');
        if(op==='app.capability')return vb(this.appCapability(vals[0]||''));
        if(op==='app.capabilities')return vl(this.appCapabilities().map(vt));
        if(op==='app.operation_supported')return vb(APP_OPERATIONS.includes(vals[0]||''));
        if(op==='app.operations')return vl(APP_OPERATIONS.map(vt));
        if(op==='app.invoke'){try{return vl([vb(true),vt(this.appInvoke(vals[0]||'',vals[1]||'{}'))]);}catch(e){return vl([vb(false),vt(String(e&&e.message||e))]);}}
        if(op==='app.invoke_async'){try{return vl([vb(true),vi(this.appInvokeAsync(vals[0]||'',vals[1]||'{}',vals[2]||''))]);}catch(e){return vl([vb(false),vt(String(e&&e.message||e))]);}}
        if(op==='app.cancel')return vb(this.appCancel(Number(vals[0]||0)));
        if(op==='app.on'){try{return vl([vb(true),vi(this.appOn(vals[0]||'',vals[1]||''))]);}catch(e){return vl([vb(false),vt(String(e&&e.message||e))]);}}
        if(op==='app.off')return vb(this.appOff(Number(vals[0]||0)));
      }
      if(op.startsWith('dom.')){
        if(!root.document)throw Error('DOM host unavailable');
        const get=()=>{const el=root.document.getElementById(vals[0]);if(!el)throw Error('DOM element not found: '+vals[0]);return el;};
        if(op==='dom.exists')return vb(!!root.document.getElementById(vals[0]));
        if(op==='dom.query_exists')return vb(!!root.document.querySelector(vals[0]));
        if(op==='dom.query_count')return vi(root.document.querySelectorAll(vals[0]).length);
        if(op==='dom.title')return vt(root.document.title||'');
        if(op==='dom.set_title'){root.document.title=vals[0]||'';return UNIT;}
        if(op==='dom.create'){const parent=root.document.getElementById(vals[0]);if(!parent)throw Error('DOM parent not found: '+vals[0]);const el=root.document.createElement(vals[1]||'div');if(vals[2])el.id=vals[2];parent.appendChild(el);return UNIT;}
        const el=get();
        if(op==='dom.set_text'){el.textContent=vals[1]||'';return UNIT;}
        if(op==='dom.text'){return vt(el.textContent==null?'':String(el.textContent));}
        if(op==='dom.set_html'){el.innerHTML=vals[1]||'';return UNIT;}
        if(op==='dom.html'){return vt(el.innerHTML==null?'':String(el.innerHTML));}
        if(op==='dom.append_html'){el.insertAdjacentHTML('beforeend',vals[1]||'');return UNIT;}
        if(op==='dom.prepend_html'){el.insertAdjacentHTML('afterbegin',vals[1]||'');return UNIT;}
        if(op==='dom.clear'){el.replaceChildren();return UNIT;}
        if(op==='dom.remove'){el.remove();return UNIT;}
        if(op==='dom.set_value'){el.value=vals[1]||'';return UNIT;}
        if(op==='dom.value'){return vt(el.value==null?'':String(el.value));}
        if(op==='dom.set_attr'){el.setAttribute(vals[1]||'',vals[2]||'');return UNIT;}
        if(op==='dom.attr'){const v=el.getAttribute(vals[1]||'');return vl([vb(v!==null),vt(v===null?'':v)]);}
        if(op==='dom.remove_attr'){el.removeAttribute(vals[1]||'');return UNIT;}
        if(op==='dom.set_style'){el.style.setProperty(vals[1]||'',vals[2]||'');return UNIT;}
        if(op==='dom.style'){return vt((root.getComputedStyle?root.getComputedStyle(el).getPropertyValue(vals[1]||''):el.style.getPropertyValue(vals[1]||''))||'');}
        if(op==='dom.add_class'){el.classList.add(vals[1]||'');return UNIT;}
        if(op==='dom.remove_class'){el.classList.remove(vals[1]||'');return UNIT;}
        if(op==='dom.toggle_class'){return vb(el.classList.toggle(vals[1]||''));}
        if(op==='dom.has_class'){return vb(el.classList.contains(vals[1]||''));}
        if(op==='dom.focus'){if(el.focus)el.focus();return UNIT;}
        if(op==='dom.blur'){if(el.blur)el.blur();return UNIT;}
        if(op==='dom.click'){if(el.click)el.click();return UNIT;}
        if(op==='dom.scroll_into_view'){if(el.scrollIntoView)el.scrollIntoView({block:'nearest'});return UNIT;}
        if(op==='dom.set_checked'){el.checked=vals[1]==='true';return UNIT;}
        if(op==='dom.checked'){return vb(!!el.checked);}
        if(op==='dom.set_disabled'){el.disabled=vals[1]==='true';return UNIT;}
        if(op==='dom.disabled'){return vb(!!el.disabled);}
        if(op==='dom.set_selected_index'){el.selectedIndex=Number(vals[1]||0);return UNIT;}
        if(op==='dom.selected_index'){return vi(Number(el.selectedIndex||0));}
        if(op==='dom.rect'){const r=el.getBoundingClientRect();return vl([vt(String(r.x)),vt(String(r.y)),vt(String(r.width)),vt(String(r.height))]);}
        if(op==='dom.on_click'){const action=vals[1]||'';el.onclick=()=>{if(typeof root.__sagaDispatch==='function')root.__sagaDispatch(['click',action,vals[0]]);};return UNIT;}
        if(op==='dom.on_event'){this.bindEvent(el,vals[1]||'click',vals[2]||'');return UNIT;}
        if(op==='dom.dispatch_event'){el.dispatchEvent(new CustomEvent(vals[1]||'saga',{detail:vals[2]||'',bubbles:true}));return UNIT;}
      }
      if(op.startsWith('storage.')){
        const area=op.startsWith('storage.session_')?root.sessionStorage:root.localStorage;
        if(!area)throw Error('storage host unavailable');
        const sub=op.replace('storage.session_','storage.');
        if(sub==='storage.set'){area.setItem(vals[0],vals[1]||'');return UNIT;}
        if(sub==='storage.get'){const v=area.getItem(vals[0]);return vl([vb(v!==null),vt(v===null?'':v)]);}
        if(sub==='storage.remove'){area.removeItem(vals[0]);return UNIT;}
        if(sub==='storage.clear'){area.clear();return UNIT;}
      }
      if(op.startsWith('cookie.')){
        if(!root.document)throw Error('cookie host unavailable');
        if(op==='cookie.set'){let c=encodeURIComponent(vals[0])+'='+encodeURIComponent(vals[1]||'')+'; Path=/; SameSite=Lax';if(vals[2])c+='; Max-Age='+Number(vals[2]);root.document.cookie=c;return UNIT;}
        if(op==='cookie.get'){const n=encodeURIComponent(vals[0])+'=';for(const c of String(root.document.cookie||'').split(';')){const q=c.trim();if(q.startsWith(n))return vl([vb(true),vt(decodeURIComponent(q.slice(n.length)))]);}return vl([vb(false),vt('')]);}
        if(op==='cookie.remove'){root.document.cookie=encodeURIComponent(vals[0])+'=; Max-Age=0; Path=/; SameSite=Lax';return UNIT;}
      }
      if(op.startsWith('nav.')){
        const loc=root.location;
        if(!loc)throw Error('navigation host unavailable');
        if(op==='nav.href')return vt(String(loc.href||''));
        if(op==='nav.path')return vt(String(loc.pathname||''));
        if(op==='nav.search')return vt(String(loc.search||''));
        if(op==='nav.hash')return vt(String(loc.hash||''));
        if(op==='nav.set_hash'){loc.hash=vals[0]||'';return UNIT;}
        if(op==='nav.navigate'){loc.assign(vals[0]);return UNIT;}
        if(op==='nav.replace'){loc.replace(vals[0]);return UNIT;}
        if(op==='nav.reload'){loc.reload();return UNIT;}
        if(op==='nav.push_state'){root.history.pushState({},'',vals[0]||'');return UNIT;}
        if(op==='nav.replace_state'){root.history.replaceState({},'',vals[0]||'');return UNIT;}
        if(op==='nav.back'){root.history.back();return UNIT;}
        if(op==='nav.forward'){root.history.forward();return UNIT;}
      }
      if(op.startsWith('timer.')){
        if(op==='timer.set_timeout'){const id=this.webState.nextId++;const h=root.setTimeout(()=>{this.webState.timers.delete(id);this.dispatchWeb('timeout',vals[1]||'',[id]);},Math.max(0,Number(vals[0]||0)));this.webState.timers.set(id,{kind:'timeout',h});return vi(id);}
        if(op==='timer.set_interval'){const id=this.webState.nextId++;const h=root.setInterval(()=>this.dispatchWeb('interval',vals[1]||'',[id]),Math.max(1,Number(vals[0]||1)));this.webState.timers.set(id,{kind:'interval',h});return vi(id);}
        if(op==='timer.animation_frame'){const id=this.webState.nextId++;const raf=root.requestAnimationFrame||((f)=>root.setTimeout(()=>f(Date.now()),16));const h=raf((ts)=>{this.webState.timers.delete(id);this.dispatchWeb('animation_frame',vals[0]||'',[id,Math.floor(ts)]);});this.webState.timers.set(id,{kind:'raf',h});return vi(id);}
        if(op==='timer.clear'){const id=Number(vals[0]);const t=this.webState.timers.get(id);if(t){if(t.kind==='interval')root.clearInterval(t.h);else if(t.kind==='raf'&&root.cancelAnimationFrame)root.cancelAnimationFrame(t.h);else root.clearTimeout(t.h);this.webState.timers.delete(id);}return UNIT;}
      }
      if(op.startsWith('net.')){
        if(op==='net.online')return vb(root.navigator?root.navigator.onLine!==false:true);
        if(op==='net.fetch'){if(typeof root.fetch!=='function')throw Error('fetch unavailable');const id=this.webState.nextId++;const ctl=new AbortController();this.webState.fetches.set(id,ctl);const method=vals[0]||'GET',url=vals[1],body=vals[2]||'',ctype=vals[3]||'text/plain',action=vals[4]||'';const opt={method,signal:ctl.signal,headers:{}};if(method!=='GET'&&method!=='HEAD'){opt.body=body;opt.headers['Content-Type']=ctype;}root.fetch(url,opt).then(async r=>{const text=await r.text();this.webState.fetches.delete(id);this.dispatchWeb('fetch',action,[id,r.status,r.ok?'true':'false',text]);}).catch(e=>{this.webState.fetches.delete(id);this.dispatchWeb('fetch_error',action,[id,String(e)]);});return vi(id);}
        if(op==='net.abort_fetch'){const id=Number(vals[0]);const c=this.webState.fetches.get(id);if(c)c.abort();this.webState.fetches.delete(id);return UNIT;}
      }
      if(op.startsWith('ws.')){
        if(typeof root.WebSocket!=='function')throw Error('WebSocket unavailable');
        if(op==='ws.open'){const id=this.webState.nextId++;const action=vals[1]||'';const ws=new root.WebSocket(vals[0]);this.webState.sockets.set(id,ws);ws.onopen=()=>this.dispatchWeb('ws_open',action,[id]);ws.onmessage=e=>this.dispatchWeb('ws_message',action,[id,typeof e.data==='string'?e.data:'<binary>']);ws.onerror=()=>this.dispatchWeb('ws_error',action,[id]);ws.onclose=e=>{this.webState.sockets.delete(id);this.dispatchWeb('ws_close',action,[id,e.code,e.reason||'']);};return vi(id);}
        const id=Number(vals[0]);const ws=this.webState.sockets.get(id);if(!ws)throw Error('WebSocket handle not found');
        if(op==='ws.send'){ws.send(vals[1]||'');return UNIT;}
        if(op==='ws.close'){ws.close(Number(vals[1]||1000),vals[2]||'');return UNIT;}
        if(op==='ws.ready_state')return vi(ws.readyState);
      }
      if(op.startsWith('canvas.')){
        if(!root.document)throw Error('canvas host unavailable');const el=root.document.getElementById(vals[0]);if(!el||typeof el.getContext!=='function')throw Error('canvas not found: '+vals[0]);const c=el.getContext('2d');if(!c)throw Error('2d canvas unavailable');
        if(op==='canvas.set_size'){el.width=Number(vals[1]);el.height=Number(vals[2]);return UNIT;}
        if(op==='canvas.clear'){c.clearRect(0,0,el.width,el.height);if(vals[1]){c.fillStyle=vals[1];c.fillRect(0,0,el.width,el.height);}return UNIT;}
        if(op==='canvas.fill_rect'){c.fillStyle=vals[5]||'#000';c.fillRect(Number(vals[1]),Number(vals[2]),Number(vals[3]),Number(vals[4]));return UNIT;}
        if(op==='canvas.stroke_rect'){c.strokeStyle=vals[5]||'#000';c.strokeRect(Number(vals[1]),Number(vals[2]),Number(vals[3]),Number(vals[4]));return UNIT;}
        if(op==='canvas.line'){c.strokeStyle=vals[5]||'#000';c.beginPath();c.moveTo(Number(vals[1]),Number(vals[2]));c.lineTo(Number(vals[3]),Number(vals[4]));c.stroke();return UNIT;}
        if(op==='canvas.circle'){c.fillStyle=vals[4]||'#000';c.beginPath();c.arc(Number(vals[1]),Number(vals[2]),Math.max(0,Number(vals[3])),0,Math.PI*2);c.fill();return UNIT;}
        if(op==='canvas.text'){c.fillStyle=vals[4]||'#000';c.font=vals[5]||'16px sans-serif';c.fillText(vals[1]||'',Number(vals[2]),Number(vals[3]));return UNIT;}
        if(op==='canvas.data_url')return vt(el.toDataURL(vals[1]||'image/png'));
      }
      if(op.startsWith('media.')){
        if(!root.document)throw Error('media host unavailable');const el=root.document.getElementById(vals[0]);if(!el)throw Error('media element not found');
        if(op==='media.play'){const p=el.play&&el.play();if(p&&p.catch)p.catch(()=>{});return UNIT;}
        if(op==='media.pause'){if(el.pause)el.pause();return UNIT;}
        if(op==='media.current_time')return vt(String(Number(el.currentTime||0)));
        if(op==='media.set_current_time'){el.currentTime=Number(vals[1]||0);return UNIT;}
        if(op==='media.volume')return vt(String(Number(el.volume==null?1:el.volume)));
        if(op==='media.set_volume'){el.volume=Math.max(0,Math.min(1,Number(vals[1]||0)));return UNIT;}
      }
      if(op.startsWith('clipboard.')){
        if(!root.navigator||!root.navigator.clipboard)throw Error('clipboard unavailable');
        if(op==='clipboard.write'){const action=vals[1]||'';root.navigator.clipboard.writeText(vals[0]||'').then(()=>this.dispatchWeb('clipboard_write',action,['true'])).catch(e=>this.dispatchWeb('clipboard_write',action,['false',String(e)]));return UNIT;}
        if(op==='clipboard.read'){const action=vals[0]||'';root.navigator.clipboard.readText().then(v=>this.dispatchWeb('clipboard_read',action,['true',v])).catch(e=>this.dispatchWeb('clipboard_read',action,['false',String(e)]));return UNIT;}
      }
      if(op.startsWith('device.')){
        const nav=root.navigator||{};
        if(op==='device.viewport_width')return vi(root.innerWidth||0);
        if(op==='device.viewport_height')return vi(root.innerHeight||0);
        if(op==='device.pixel_ratio')return vt(String(root.devicePixelRatio||1));
        if(op==='device.language')return vt(String(nav.language||''));
        if(op==='device.user_agent')return vt(String(nav.userAgent||''));
        if(op==='device.visibility')return vt(root.document?String(root.document.visibilityState||'visible'):'unknown');
      }
      if(op.startsWith('geo.')){
        if(!root.navigator||!root.navigator.geolocation)throw Error('geolocation unavailable');const action=vals[0]||'';root.navigator.geolocation.getCurrentPosition(p=>this.dispatchWeb('geolocation',action,['true',p.coords.latitude,p.coords.longitude,p.coords.accuracy]),e=>this.dispatchWeb('geolocation',action,['false',e.code,e.message]));return UNIT;
      }
      if(op.startsWith('fullscreen.')){
        if(!root.document)throw Error('fullscreen unavailable');
        if(op==='fullscreen.request'){const el=root.document.getElementById(vals[0]);if(!el||!el.requestFullscreen)throw Error('fullscreen unavailable');const p=el.requestFullscreen();if(p&&p.catch)p.catch(()=>{});return UNIT;}
        if(op==='fullscreen.exit'){const p=root.document.exitFullscreen&&root.document.exitFullscreen();if(p&&p.catch)p.catch(()=>{});return UNIT;}
        if(op==='fullscreen.active')return vb(!!root.document.fullscreenElement);
      }
      throw Error('unknown host operation '+op);
    }
    builtin(name,args) {
      const n=args.length;
      if(name==='len'){if(n!==1)throw Error('len arity');const a=args[0];if(a.k==='text')return vi(bytes(a.v).length);if(a.k==='list')return vi(a.v.length);throw Error('len type');}
      if(name==='append'){if(n!==2||args[0].k!=='list')throw Error('append type');return vl(args[0].v.map(clone).concat([clone(args[1])]));}
      if(name==='set_at'){if(n!==3||args[0].k!=='list'||args[1].k!=='int')throw Error('set_at type');const r=args[0].v.map(clone),i=Number(args[1].v);if(i<0||i>=r.length)throw Error('set_at range');r[i]=clone(args[2]);return vl(r);}
      if(name==='push'){if(n!==2||args[0].k!=='list')throw Error('push type');args[0].v.push(clone(args[1]));return clone(args[0]);}
      if(name==='substring'){if(n!==3||args[0].k!=='text')throw Error('substring type');return vt(byteSubstring(args[0].v,args[1].v,args[2].v));}
      if(name==='slice'){if(n!==3||args[0].k!=='list')throw Error('slice type');let a=Math.max(0,Number(args[1].v)),b=Math.max(a,Number(args[2].v));return vl(args[0].v.slice(a,b).map(clone));}
      if(name==='find_text'){if(n!==2||args[0].k!=='text'||args[1].k!=='text')throw Error('find_text type');return vi(byteFind(args[0].v,args[1].v));}
      if(name==='replace'){if(n!==3||args.some(x=>x.k!=='text'))throw Error('replace type');return vt(args[0].v.split(args[1].v).join(args[2].v));}
      if(name==='byteord'){if(n!==1||args[0].k!=='text'||!bytes(args[0].v).length)throw Error('byteord type');return vi(bytes(args[0].v)[0]);}
      if(name==='bytechr'){if(n!==1||args[0].k!=='int'||args[0].v<0n||args[0].v>255n)throw Error('bytechr type');return vt(fromBytes(Uint8Array.of(Number(args[0].v))));}
      if(name==='starts_with'){if(n!==2||args.some(x=>x.k!=='text'))throw Error('starts_with type');return vb(byteStarts(args[0].v,args[1].v));}
      if(name==='ends_with'){if(n!==2||args.some(x=>x.k!=='text'))throw Error('ends_with type');return vb(byteEnds(args[0].v,args[1].v));}
      if(name==='text'){if(n!==1)throw Error('text arity');return vt(textOf(args[0]));}
      if(name==='int'){if(n!==1)throw Error('int arity');const a=args[0];if(a.k==='int')return a;if(a.k==='bool')return vi(a.v?1:0);if(a.k==='text'&&/^[+-]?\d+$/.test(a.v))return vi(BigInt(a.v));throw Error('int parse/type');}
      if(name==='ord'){if(n!==1||args[0].k!=='text'||bytes(args[0].v).length!==1)throw Error('ord type');return vi(bytes(args[0].v)[0]);}
      if(name==='chr'){if(n!==1||args[0].k!=='int'||args[0].v<0n||args[0].v>127n)throw Error('chr type');return vt(String.fromCharCode(Number(args[0].v)));}
      if(name==='read_text'){if(n!==1||args[0].k!=='text')throw Error('read_text type');const key=args[0].v;if(!(key in this.files))throw Error('virtual file not found: '+key);return vt(this.files[key]);}
      if(name==='write_text'){if(n!==2||args[0].k!=='text'||args[1].k!=='text')throw Error('write_text type');this.files[args[0].v]=args[1].v;return UNIT;}
      if(name==='args'){return vl(this.args.map(vt));}
      if(name==='host_available'){if(n!==1||args[0].k!=='text')throw Error('host_available type');const cap=args[0].v;if(cap==='dom'||cap==='canvas'||cap==='media'||cap==='cookie'||cap==='navigation'||cap==='fullscreen')return vb(safeFeature(()=>root.document));if(cap==='storage')return vb(safeFeature(()=>root.localStorage));if(cap==='session')return vb(safeFeature(()=>root.sessionStorage));if(cap==='timer')return vb(typeof root.setTimeout==='function');if(cap==='fetch')return vb(typeof root.fetch==='function');if(cap==='websocket')return vb(typeof root.WebSocket==='function');if(cap==='clipboard')return vb(safeFeature(()=>root.navigator&&root.navigator.clipboard));if(cap==='geolocation')return vb(safeFeature(()=>root.navigator&&root.navigator.geolocation));if(cap==='device')return vb(safeFeature(()=>root.navigator));if(cap==='app')return vb(true);return vb(false);}
      if(name==='host_call'){if(n!==2||args[0].k!=='text'||args[1].k!=='list')throw Error('host_call type');return this.hostCall(args[0].v,args[1].v);}
      if(name==='exit'){if(n!==1||args[0].k!=='int')throw Error('exit type');throw new VMExit(args[0].v);}
      throw Error('unknown builtin '+name);
    }
    execFunc(f, argv, depth=0) {
      if(depth>this.maxDepth)throw Error('call depth exceeded');
      if(argv.length!==f.argc)throw Error('arity mismatch '+f.name);
      const loc=Array(Math.max(f.locals,f.argc)).fill(UNIT); for(let i=0;i<argv.length;i++)loc[i]=clone(argv[i]);
      const st=[]; let pc=0, ret=UNIT;
      const pop=()=>{if(!st.length)throw Error('stack underflow');return st.pop();};
      while(pc<f.code.length){const ins=f.code[pc++],op=ins.op;
        if(op==='PUSHI')st.push(vi(ins.a)); else if(op==='PUSHB')st.push(vb(Number(ins.a)!==0)); else if(op==='PUSHU')st.push(UNIT); else if(op==='PUSHS')st.push(vt(unhex(ins.a)));
        else if(op==='LOAD')st.push(clone(loc[Number(ins.a)])); else if(op==='STORE')loc[Number(ins.a)]=pop(); else if(op==='GLOAD')st.push(clone(this.program.globals[Number(ins.a)])); else if(op==='GSTORE')this.program.globals[Number(ins.a)]=pop();
        else if(op==='POP')pop(); else if(op==='DUP')st.push(clone(st[st.length-1])); else if(op==='NEG'){const a=pop();if(a.k!=='int')throw Error('NEG type');st.push(vi(-a.v));} else if(op==='NOT')st.push(vb(!truth(pop())));
        else if(['ADD','SUB','MUL','DIV','MOD'].includes(op)){const b=pop(),a=pop();if(op==='ADD'&&a.k==='text'&&b.k==='text'){st.push(vt(a.v+b.v));}else{if(!['int','bool'].includes(a.k)||!['int','bool'].includes(b.k))throw Error('arithmetic type');const av=a.k==='bool'?(a.v?1n:0n):a.v,bv=b.k==='bool'?(b.v?1n:0n):b.v;if((op==='DIV'||op==='MOD')&&bv===0n)throw Error('division by zero');st.push(vi(op==='ADD'?av+bv:op==='SUB'?av-bv:op==='MUL'?av*bv:op==='DIV'?av/bv:av%bv));}}
        else if(['EQ','NE','LT','LE','GT','GE'].includes(op)){const b=pop(),a=pop();let z=false;if(a.k==='int'&&b.k==='int'){z=op==='EQ'?a.v===b.v:op==='NE'?a.v!==b.v:op==='LT'?a.v<b.v:op==='LE'?a.v<=b.v:op==='GT'?a.v>b.v:a.v>=b.v;}else if(a.k==='text'&&b.k==='text'){z=op==='EQ'?a.v===b.v:op==='NE'?a.v!==b.v:op==='LT'?a.v<b.v:op==='LE'?a.v<=b.v:op==='GT'?a.v>b.v:a.v>=b.v;}else if(op==='EQ'||op==='NE'){z=(a.k===b.k&&textOf(a)===textOf(b));if(op==='NE')z=!z;}else throw Error('comparison type');st.push(vb(z));}
        else if(op==='JMP')pc=f.labels.get(ins.a); else if(op==='JZ'){if(!truth(pop()))pc=f.labels.get(ins.a);}
        else if(op==='CALL'){const name=unhex(ins.a),n=Number(ins.b),aa=Array(n);for(let i=n-1;i>=0;i--)aa[i]=pop();const g=this.program.funcs.get(name);if(!g)throw Error('unknown function '+name);st.push(this.execFunc(g,aa,depth+1));}
        else if(op==='CALLB'){const name=unhex(ins.a),n=Number(ins.b),aa=Array(n);for(let i=n-1;i>=0;i--)aa[i]=pop();st.push(this.builtin(name,aa));}
        else if(op==='MKLIST'){const n=Number(ins.a),aa=Array(n);for(let i=n-1;i>=0;i--)aa[i]=pop();st.push(vl(aa));}
        else if(op==='GETIDX'){const idx=pop(),a=pop();if(idx.k!=='int')throw Error('index type');const k=Number(idx.v);if(a.k==='list'){if(k<0||k>=a.v.length)throw Error('index range');st.push(clone(a.v[k]));}else if(a.k==='text'){const q=bytes(a.v);if(k<0||k>=q.length)throw Error('text index range');st.push(vt(fromBytes(q.slice(k,k+1))));}else throw Error('index receiver');}
        else if(op==='SETIDX'){const v=pop(),idx=pop(),a=pop(),k=Number(idx.v);if(a.k!=='list'||k<0||k>=a.v.length)throw Error('setindex type/range');a.v[k]=clone(v);st.push(a);}
        else if(op==='PRINT'){const s=textOf(pop());this.stdout(s+'\n');st.push(UNIT);}
        else if(op==='RET'){ret=st.length?pop():UNIT;return ret;} else throw Error('unknown opcode '+op);
      }
      return st.length?pop():ret;
    }
    run() {
      const f=this.program.funcs.get(this.program.entry); if(!f)throw Error('entry not found');
      try { const r=this.execFunc(f,[]); return {code:r&&r.k==='int'?Number(r.v):0, files:this.files}; }
      catch(e){ if(e instanceof VMExit)return {code:e.code,files:this.files}; throw e; }
    }
  }
  function runSagaSH3(programText, args, files, stdout) { return new SagaSH3VM(programText,{args,files,stdout}).run(); }
  root.SagaSH3VM=SagaSH3VM; root.runSagaSH3=runSagaSH3;
  if(typeof module!=='undefined'&&module.exports)module.exports={SagaSH3VM,runSagaSH3};
})(typeof globalThis!=='undefined'?globalThis:this);
