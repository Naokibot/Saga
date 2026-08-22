# Saga 0.21.0 Feature Audit

## Retained language depth

Standard Core 1.0 RC1 and Edition 2027 Preview remain intact: static typing/inference, exact numbers, floats/fixed integers, collections, closures, OOP/interfaces/generics/associated types, option/result, records/enums/match, resource ownership, structured concurrency, derive/comptime, unsafe boundaries, diagnostics and modules.

## Official implementation

Official `saga-sh3` remains SH-3 qualified. The canonical compiler/lowering and lexer/parser/checker/runtime/loader/built-ins remain Saga source. Go and Python trees remain reference/hosted implementations and validation comparators rather than the official semantic kernel.

## New application profiles

### Web/PWA

- static `web` target using SH-3 browser VM + canonical Saga kernel;
- installable/offline `pwa` target;
- DOM text/HTML/value/attribute operations;
- localStorage;
- click redispatch via `sys.args()`;
- source-unit collection into a virtual browser filesystem.

### Backend

- real HTTP listen/accept/respond server API;
- request method/path/body/header/query accessors;
- close-safe accept and response write acknowledgement;
- 8 MiB request body cap.

### Persistence

- optimistic begin/get/put/delete/commit/rollback transactions;
- conflict detection within an opened DB state;
- path-serialized atomic replacement.

### 3D

- game API inventory: **101** typed functions;
- cube/custom/OBJ meshes;
- translation/rotation/scale;
- perspective camera;
- filled CPU rasterizer with depth buffer;
- wireframe renderer.

### Systems

- `sys.platform`, `sys.arch`, `sys.cpu_count`, `sys.page_size`.

## Deliberate limits

- PWA is not a native iOS/Android SDK.
- DOM host APIs are a practical imperative baseline, not a mature reactive frontend framework.
- HTTP server is a baseline, not a complete production web framework/TLS/middleware stack.
- built-in transaction DB is not multi-process relational ACID.
- CPU 3D is not a PBR/skeletal/scene/GPU AAA engine.
- existing bare-metal support is not a complete general-purpose operating system/kernel ecosystem.
