package main

import (
	"embed"
	"encoding/json"
	"fmt"
	"html"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

//go:embed web_runtime/sh3vm-browser.js web_runtime/kernel.sbc
var sagaWebRuntime embed.FS

var sagaSourceUseRE = regexp.MustCompile(`(?m)^\s*use\s+"([^"]+\.saga)"`)

func collectWebSourceTree(entry string) (map[string]string, string, error) {
	abs, err := filepath.Abs(entry)
	if err != nil {
		return nil, "", err
	}
	root := filepath.Dir(abs)
	files := map[string]string{}
	seen := map[string]bool{}
	var walk func(string) error
	walk = func(real string) error {
		real, err = filepath.Abs(real)
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(root, real)
		if err != nil {
			return err
		}
		if rel == ".." || strings.HasPrefix(rel, ".."+string(filepath.Separator)) {
			return fmt.Errorf("web target source unit escapes project root: %s", real)
		}
		if seen[real] {
			return nil
		}
		seen[real] = true
		b, err := os.ReadFile(real)
		if err != nil {
			return err
		}
		src := string(b)
		virt := "/app/" + filepath.ToSlash(rel)
		files[virt] = src
		for _, m := range sagaSourceUseRE.FindAllStringSubmatch(src, -1) {
			dep := filepath.Clean(filepath.Join(filepath.Dir(real), filepath.FromSlash(m[1])))
			if err := walk(dep); err != nil {
				return err
			}
		}
		return nil
	}
	if err := walk(abs); err != nil {
		return nil, "", err
	}
	rel, _ := filepath.Rel(root, abs)
	return files, "/app/" + filepath.ToSlash(rel), nil
}

func writeWebBundle(entry, output string, pwa bool) (string, error) {
	stmts, err := loadProgram(entry)
	if err != nil {
		return "", err
	}
	c := NewChecker()
	if err := c.Check(stmts); err != nil {
		return "", err
	}
	files, virtualEntry, err := collectWebSourceTree(entry)
	if err != nil {
		return "", err
	}
	runtimeJS, err := sagaWebRuntime.ReadFile("web_runtime/sh3vm-browser.js")
	if err != nil {
		return "", err
	}
	kernel, err := sagaWebRuntime.ReadFile("web_runtime/kernel.sbc")
	if err != nil {
		return "", err
	}
	if output == "" {
		base := strings.TrimSuffix(filepath.Base(entry), filepath.Ext(entry))
		output = base + "-web"
	}
	if err := os.RemoveAll(output); err != nil {
		return "", err
	}
	if err := os.MkdirAll(output, 0755); err != nil {
		return "", err
	}
	if err := os.WriteFile(filepath.Join(output, "saga-sh3-browser.js"), runtimeJS, 0644); err != nil {
		return "", err
	}
	if err := os.WriteFile(filepath.Join(output, "kernel.sbc"), kernel, 0644); err != nil {
		return "", err
	}
	fileJSON, _ := json.Marshal(files)
	if err := os.WriteFile(filepath.Join(output, "sources.json"), append(fileJSON, '\n'), 0644); err != nil {
		return "", err
	}
	entryJSON, _ := json.Marshal(virtualEntry)
	appJS := fmt.Sprintf(`(function(){
const files=%s;
const entry=%s;
let kernel='';
const out=(s)=>{const e=document.getElementById('saga-output');if(e)e.textContent+=s;};
function run(extra){
 const status=document.getElementById('saga-status');if(status)status.textContent='Saga running';
 try {
  const result=runSagaSH3(kernel,['run',entry].concat(extra||[]),files,out);
  if(status)status.textContent=result.code===0?'Saga finished':'Saga exited '+result.code;
 } catch(err){if(status)status.textContent='Saga error';out(String(err)+'\n');console.error(err);}
}
globalThis.__sagaDispatch=(args)=>run(args||[]);
fetch('kernel.sbc').then(r=>{if(!r.ok)throw new Error('kernel.sbc '+r.status);return r.text();}).then(k=>{kernel=k;run([]);}).catch(err=>{const e=document.getElementById('saga-status');if(e)e.textContent='Saga error';out(String(err)+'\n');console.error(err);});
})();
`, fileJSON, entryJSON)
	if err := os.WriteFile(filepath.Join(output, "app.js"), []byte(appJS), 0644); err != nil {
		return "", err
	}
	title := html.EscapeString(strings.TrimSuffix(filepath.Base(entry), filepath.Ext(entry)))
	manifestLink := ""
	sw := ""
	if pwa {
		manifestLink = `<link rel="manifest" href="manifest.webmanifest">`
		sw = `<script>if('serviceWorker' in navigator){navigator.serviceWorker.register('./service-worker.js');}</script>`
		manifest := map[string]any{"name": title, "short_name": title, "start_url": "./", "display": "standalone", "background_color": "#ffffff", "theme_color": "#111111", "icons": []any{}}
		mb, _ := json.MarshalIndent(manifest, "", "  ")
		if err := os.WriteFile(filepath.Join(output, "manifest.webmanifest"), append(mb, '\n'), 0644); err != nil {
			return "", err
		}
		assets := []string{"./", "./index.html", "./app.js", "./saga-sh3-browser.js", "./kernel.sbc", "./sources.json", "./saga-web.json"}
		sort.Strings(assets)
		ab, _ := json.Marshal(assets)
		worker := fmt.Sprintf("const CACHE='saga-pwa-%s';const ASSETS=%s;self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS)).then(()=>self.skipWaiting())));self.addEventListener('activate',e=>e.waitUntil(Promise.all([self.clients.claim(),caches.keys().then(keys=>Promise.all(keys.filter(k=>k!==CACHE).map(k=>caches.delete(k))))])));self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(caches.match(e.request).then(r=>r||fetch(e.request).then(resp=>{const copy=resp.clone();caches.open(CACHE).then(c=>c.put(e.request,copy));return resp;}).catch(()=>e.request.mode==='navigate'?caches.match('./index.html'):Promise.reject(new Error('offline')))))});\n", sagaGoVersion, ab)
		if err := os.WriteFile(filepath.Join(output, "service-worker.js"), []byte(worker), 0644); err != nil {
			return "", err
		}
	}
	page := fmt.Sprintf(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title>%s<style>body{font-family:ui-monospace,monospace;max-width:900px;margin:2rem auto;padding:0 1rem}pre{white-space:pre-wrap;background:#f5f5f5;padding:1rem;border-radius:.5rem}#saga-status{font-family:system-ui,sans-serif;color:#555}</style></head><body data-saga-release="%s"><h1>%s</h1><p id="saga-status">Starting Saga…</p><main id="saga-root"></main><pre id="saga-output"></pre><script src="saga-sh3-browser.js"></script><script src="app.js"></script>%s</body></html>`, title, manifestLink, sagaGoVersion, title, sw)
	if err := os.WriteFile(filepath.Join(output, "index.html"), []byte(page), 0644); err != nil {
		return "", err
	}
	meta := map[string]any{"schema": 1, "saga": sagaGoVersion, "target": map[bool]string{true: "pwa", false: "web"}[pwa], "entry": virtualEntry, "source_units": len(files), "runtime": "SH-3 browser VM + canonical Saga kernel", "offline": pwa}
	jb, _ := json.MarshalIndent(meta, "", "  ")
	if err := os.WriteFile(filepath.Join(output, "saga-web.json"), append(jb, '\n'), 0644); err != nil {
		return "", err
	}
	return output, nil
}
