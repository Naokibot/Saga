# Saga 0.31.0 Validation — Native Object + Incremental Build/Link

This report is updated from executable evidence in the release tree. It distinguishes local Linux validation from unexecuted physical host qualification.

## Native object qualification

`tools/native_object_qualification.py` verifies:

- two-source/module first build emits two native relocatable objects;
- linked executable runs;
- no-change rebuild compiles zero source objects and skips link;
- implementation-only dependency change rebuilds only the dependency object;
- public ABI change invalidates the importer object;
- object tamper is detected by SHA-256 and repaired;
- two clean builds in different build directories are byte-reproducible on the same host/toolchain;
- a dedicated regression test launches two build processes against the same cold build directory and verifies a valid final state/output after serialized publication.

## Regression boundary

The existing language, module, LSP, ecosystem, security, machine-control, concurrency and prior review test inventories are rerun before release packaging. Platform/evidence tests are rerun after the final source manifest is fixed.

## Host qualification

Validated in this environment:

- Linux x86-64;
- Go 1.23.2;
- Clang 17.0.0;
- ELF relocatable objects;
- static Go C-archive + native host link.

Not claimed by this report:

- physical Windows object/link qualification;
- physical macOS object/link qualification;
- COFF/Mach-O reproducibility evidence;
- full direct machine-code lowering of Standard Core.
## Final regression evidence

- Python non-platform unittest inventory: **339 / 339 PASS**; Platform/Evidence: **9 / 9 PASS**; total Python unittest inventory: **348 / 348 PASS**.
- Go implementation: `go test ./...` PASS.
- Python Self Conformance: **44 / 44 PASS**.
- Go Self Conformance: **44 / 44 PASS**.
- Parser fuzz: 100,000 cases; expression fuzz: 25,000 cases; unexpected host exceptions: **0**.
- Native Object qualification: PASS, including real relocatable objects, complete cache hit, implementation-only invalidation, public-ABI invalidation and same-host/toolchain reproducibility.
- 0.31 Native Game/Web Host/Security/App Action compatibility validators: PASS.

Platform/Evidence tests passed **9 / 9** against the source-manifest workflow. After this report is included in the source tree, the manifest is regenerated once more and the same nine tests are rerun against that exact final tree.

