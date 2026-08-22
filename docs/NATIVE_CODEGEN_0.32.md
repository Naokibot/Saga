# Native Codegen 0.32 — usage

Saga 0.32 adds a direct native-function profile alongside the complete Standard
Runtime profile and the 0.31 runtime-object profile.

## Build

```bash
saga build examples/native_codegen/main.saga \
  --target native \
  --profile codegen \
  --build-dir .saga-build/codegen \
  --output ./native-demo
```

The build report states `go_runtime=false`.

## Inspect native symbols

On ELF/macOS hosts:

```bash
nm .saga-build/codegen/objects/*.o
```

A caller module shows the imported Saga function as `U`; the callee module shows
that same ABI 0.32 symbol as `T`.

`abi/*.nabi.json` gives the stable machine-readable ABI and `abi/*.nabi.h` gives
C declarations for public functions.

## Incremental behavior

Run the same command twice. The second build reports no compiled objects and no
link. Editing only a dependency function body recompiles only that module.
Changing its public function signature invalidates importer objects through the
native ABI hash.

## Choosing a profile

- `standard`: complete Standard Core through the standalone Go runtime.
- `object`: complete Standard Core represented as independently linked runtime
  payload objects; ABI-aware incremental linking.
- `codegen`: direct machine-code functions and direct module symbol calls for the
  ABI 0.32 subset; no Go runtime in the linked executable.
- `scalar`: older single-unit checked direct-C deployment subset.

Use `codegen` only when every construct in the source graph is part of the
specified ABI 0.32 direct subset. It intentionally fails rather than changing
semantics.
