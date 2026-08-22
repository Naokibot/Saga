# Saga Web Application Profile 0.21

**Status:** implementation profile for Saga 0.21.0. This is not a W3C, WHATWG, ISO/IEC, Android, or Apple standard.

## Goal

Run the canonical Saga SH-3 language kernel in ordinary browsers without requiring a server-side language runtime. `saga build app.saga --target web` emits a static browser bundle; `--target pwa` additionally emits an installable/offline service-worker profile.

## Bundle

A bundle contains the language-neutral JavaScript SH3 VM, canonical Saga kernel bytecode, Saga source units, loader metadata, and the bootstrap page. PWA bundles additionally contain `manifest.webmanifest` and `service-worker.js` and cache all language/runtime/source assets needed for offline startup.

## Browser host surface

`use web` exposes browser capabilities when the browser host is available:

- `browser_available() -> bool`
- `set_text(id,text) -> result[unit,text]`
- `set_html(id,html) -> result[unit,text]`
- `set_value(id,text) -> result[unit,text]`
- `value(id) -> result[text,text]`
- `set_attr(id,name,value) -> result[unit,text]`
- `on_click(id,action) -> result[unit,text]`
- `storage_set(key,value) -> result[unit,text]`
- `storage_get(key) -> result[option[text],text]`
- `storage_remove(key) -> result[unit,text]`

`on_click` redispatches the same Saga entry point with `sys.args()` containing `click`, the action, and the element id. Persistent UI state can be stored in browser local storage. Browser capabilities fail closed on non-browser hosts.

`set_html` is intentionally raw HTML and is an unsafe-content boundary at the application layer: untrusted values must be escaped before interpolation.

## Scope boundary

This profile is a practical browser/PWA application baseline. It is not yet a React/Vue-equivalent virtual-DOM framework, SSR framework, native Android/iOS SDK, or WebGPU 3D framework.
