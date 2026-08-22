# Saga 0.32.0 Validation — Native Codegen ABI

## Result summary

- Native Codegen dedicated regression: **8 / 8 PASS**.
- Native Codegen qualification: **17 / 17 PASS**.
- Existing non-platform Python regression inventory executed in split groups:
  **347 / 347 PASS** before final source-manifest qualification.
- Python Self Conformance: **44 / 44 PASS**.
- Go Self Conformance: **44 / 44 PASS**.
- Go implementation: `go test ./...` **PASS**.
- Specification review lint: **PASS**.
- Parser fuzz: **100,000 cases**.
- Expression fuzz: **25,000 cases**.
- Unexpected host exceptions in fuzz: **0**.

- Platform/Evidence regression: **9 / 9 PASS**.
- Complete Python unittest inventory: **356 / 356 PASS** (347 non-platform + 9 platform).
- Python ↔ Go common differential: **44 / 44 PASS**.
- Namespaced module graph differential: **12 / 12 PASS**.
- Internal automated security audit: **PASS** with zero reported critical/high issues.
- Final source manifest: **self-verification PASS**.

Source-bound JSON evidence is stored under `validation/`; the normative source
tree digest is recorded in `release/source-manifest-0.32.0.json`.

## Direct-native qualification

The qualification suite verifies:

1. a working native executable whose link report states `go_runtime_linked=false`;
2. real relocatable module objects;
3. a direct callee machine-code symbol in the dependency object;
4. an undefined relocation for that symbol in the caller object;
5. disassembly of the Saga function body;
6. absence of characteristic Go runtime symbols in the final executable;
7. generated `.nabi.json` and `.nabi.h` public ABI artifacts;
8. a separately compiled C client directly calling the Saga module symbol;
9. complete unchanged-build cache hit;
10. implementation-only dependency invalidation;
11. public ABI importer invalidation;
12. clean-build object and executable byte reproducibility;
13. fail-closed rejection of unsupported ABI value types.

## Physical environment actually exercised

The new ABI was physically executed on the available Linux x86-64 environment
using the installed clang/cc toolchain. The report does not infer Windows COFF or
macOS Mach-O qualification from source code branches alone.

## Meaning of `direct native`

In the `codegen` profile, supported Saga top-level functions are direct native
functions. Module-to-module Saga calls do not route through the Go Standard
Runtime. A small C support object remains for checked primitive arithmetic and
primitive output; this is part of the ABI, not an interpreter/runtime dispatch
engine.

Full Standard Core continues to use `standard` or `object` when a feature is
outside ABI 0.32.
