# Saga 0.12.0 general-purpose capability map

Saga is intended to be a general-purpose language. “General purpose” does not mean every domain-specific framework is built into Standard Core; ordinary language semantics are in Standard Core and host-specific services are provided by capability-controlled Hosted Standard modules/adapters.

## Standard Core in both Python and Go implementations

- variables (`let`/`var`), expressions, exact arithmetic, booleans and text;
- named and nested lexical functions, closures with captured cells, recursion and higher-order operations;
- `if`, `while`, inclusive range `for`, `return`, `break`, `continue`;
- lists, maps, sets and `option[T]`;
- generic functions/classes and type checking;
- classes, inheritance, interfaces, abstract classes, polymorphism, private members and annotations;
- exceptions with `try`/`catch`/`finally`/`throw`;
- source units and multi-file projects;
- isolated tasks and deterministic core evaluation rules;
- UTF-8/Unicode 15.1 identifier profile;
- stable machine-readable diagnostics;
- project metadata, lock/verify and canonical `.sagapkg` source packages.

## Hosted Standard in the Python reference implementation

The current build exposes 27 hosted modules / 149 functions. Major areas include:

- console input/output and regular expressions;
- text/binary file I/O, paths, JSON/CSV/data handling;
- date/time;
- SQLite, transactions, ORM and document storage;
- HTTP client/server, TCP/UDP and WebSocket;
- thread/future concurrency plus process-based CPU parallel map/filter/reduce;
- process execution without implicit shell;
- GUI/event handling;
- cryptography primitives/adapters and secure random;
- image/video/game adapters;
- scientific/statistical helpers and ML adapters;
- GPIO/IoT, Spark and cloud adapters;
- reflection and capability-controlled extension/plugin interfaces;
- host platform/system information.

## Explicit boundaries

- Standard Core deliberately excludes operating-system APIs and third-party frameworks.
- Android/iOS native SDKs, full browser DOM runtimes, GPU kernels, distributed databases, commercial cloud products, and large AI frameworks are integrations/adapters rather than language semantics.
- Python plugins are optional Hosted Standard extensions and are not required for ordinary Saga programs.


## 0.11 ecosystem/compiler additions

- reference HTTP package registry plus SHA-256-verified, fixed-version `pkg:` imports;
- deployable registry server template and package author SDK;
- isolated Python bridge and WIT/WASM component authoring templates;
- native/WASM `standard` runtime-AOT bundles and a direct `scalar` C lowering profile;
- iOS Swift Package native runtime source generator and Android JNI/CMake native project generator;
- static capability preview with `saga capabilities`.

These features create ecosystem infrastructure and bridges; they do not imply that a public Internet registry is already operated, that App Store/Play Store distribution is certified, or that a large third-party Saga-native package population already exists.
