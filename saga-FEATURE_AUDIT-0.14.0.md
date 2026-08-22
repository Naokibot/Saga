# Saga 0.14.0 feature audit

## Standard Core / Language Edition 1.0 RC1

Implemented in Saga Native: immutable/mutable bindings, static typing and inference, exact integers/decimals/rationals, bool-only control conditions, lists/maps/sets, functions and recursion, higher-order functions, lexical closures, classes, generic classes, generic inheritance, generic interfaces, abstract classes, polymorphism, private members, annotations, exceptions, `option[T]`, `result[T,E]`, enums, records, exhaustive `match`, interpolation, multi-source projects, isolated tasks, standard test declarations, stable structured diagnostics and Unicode identifiers.

## Official development tools

`run`, `check`, `build`, `test`, `fmt`, `lint`, `repl`, `debug`, `lsp`, `codegen json`, `codegen sql`, `lock`, `verify`, `pack`, `registry`, `capabilities`, `learn`, `explain`, `conformance`, `doctor`, `info`, and the optional interoperability-only `transpile-python` exporter.

## Native Hosted library

Automated inventory after game expansion: **52/52 functions exercised**.

- io: 5
- json: 2
- time: 2
- math: 4
- random: 2
- crypto: 1
- net: 6
- http: 3
- db: 6
- process: 1
- regex: 2
- game: 18

These APIs are part of the Native distribution and do not require another programming-language runtime. The API smoke test uses real temporary files, real localhost TCP, a real local HTTP test server, persistent DB files, process argv execution, regex operations and real game-canvas operations.

## Game development

The dependency-free game baseline supports a 2D text-cell canvas, clear/set/text/box drawing, filled rectangles, Bresenham lines, circle outlines, multiline sprites, pure render, terminal presentation, frame pacing, input, rectangle and point collision, clock, width and height. `examples/game/mini_dodge.saga` and `examples/game/shape_arena.saga` execute on Saga Native alone. Hardware-accelerated graphics/audio/gamepads are not claimed as implemented.

## Build targets

- Native standalone: complete Standard Core runtime-AOT bundle, deterministic and self-contained.
- WASM scalar: direct WebAssembly code generation for the documented integer/bool subset; unsupported constructs are rejected.
- Python source exporter: optional interoperability output only; never required to use Saga.

## International-use engineering

UTF-8 source, vendored Unicode 15.1 XID/NFC profile, stable diagnostic IDs independent of translations, UTF-16-compatible LSP positions, reproducible packages, signed packages with explicit publisher trust, self-host compiler fixed point, and a normative English specification are included. English is the complete fallback catalog; Japanese has broad translations; French/Spanish/German are partial and fall back to English.
