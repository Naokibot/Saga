# Saga 0.23.0 feature audit

## Language

Language Edition 1.0 RC1 and Edition 2027 Preview remain available with static types/inference, exact numbers plus explicit floats/fixed integers, closures, OOP/interfaces/generics/associated types, enums/records/match, option/result/`?`, exceptions, resource/move/using/defer, structured concurrency, derivation/comptime, modules and diagnostics v2.

## Application APIs

- `app`: 10 source APIs implementing Universal App Action Protocol.
- Browser Universal App profile: 53 first-party operation identifiers.
- `web`: 107 functions / 101 Browser Host operations.
- `game`: 101 typed APIs including portable 2D and CPU 3D baseline.
- Native Hosted: io/json/time/math/random/crypto/net/http/db/process/regex/task/sys/compiler plus capability-gated web/app/embedded and optional ffi/jit.

The Universal App protocol makes arbitrary future/vendor actions representable as namespaced operations with JSON payloads, but representation does not fabricate a host implementation.

## Browser

Real Chromium 144 Blink/V8 integration passes canonical SH-3 Saga execution, DOM/Canvas/events/Fetch and Universal App sync/async/lifecycle paths. Enterprise top-level URL policy is respected rather than bypassed.

## Systems/profiles

C ABI Profile 2, bare-metal Cortex-M baseline, no-import WASM, shader/compute IR, HTTP server and DB transaction profiles from prior releases remain in the source tree.

## Toolchain

`run`, `check`, `build`, `test`, `fmt`, `lint`, `repl`, `debug`, `lsp`, `lock`, `verify`, `pack`, `registry`, `capabilities`, `learn`, `explain`, `conformance`, `doctor`, `info` and existing code-generation/standards tools remain present in the reference toolchains.

## Self-hosting

Official SH-3 compiler and canonical language kernel remain Saga source. Compiler and kernel fixed points are byte-identical at Stage2/Stage3; Standard Core 23/23, diagnostics 11/11, Edition 2027 15/15 and source-boundary audit 0 problems pass in split qualification.

## Explicit non-claims

- No claim that every vendor/hardware operation has been physically executed.
- No claim that Android/iOS proprietary adapters are device-qualified in this release.
- No claim that Chromium service-worker navigation passed through the host's enterprise URL block policy.
- Internal review is not third-party certification.
