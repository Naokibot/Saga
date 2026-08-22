# Saga 0.30.0 Natural Module Core — Review Report

## Scope

This review covered implementation of a shared namespaced-module model across the Python reference and independent Go implementations, plus the separate-interface boundary, runtime semantics, standalone/mobile packaging and regression safety.

## Design review

### Accepted decisions

1. Module declarations are explicit and leading.
2. Top-level declarations are internal by default.
3. `public`/`internal` are the official visibility vocabulary.
4. Imports are qualified namespaces; wildcard flattening is not added.
5. Qualified nominal identity is preserved (`a.User != b.User`).
6. Legacy module-less source units remain flattened for compatibility.
7. Public APIs cannot accidentally leak internal or dependency-alias nominal types in 0.30.
8. `.smi.json` is a deterministic frontend ABI artifact, not executable code.
9. Dependency invalidation is driven by dependency ABI, not dependency source bytes alone.
10. Stale or damaged interfaces fail safe to source checking when source is available.

## Defects found and fixed during implementation

- Python and Go initially disagreed on project-root discovery for sources below `src/`.
- Python separate compilation initially used the module directory rather than the `saga.toml` project root.
- Qualified imported base classes type-checked but were not initially resolved by the Python/Go runtime inheritance path.
- SMI-reconstructed derived classes initially lost inherited constructor fields.
- Re-importing the same canonical module through explicit/default alias forms could bypass canonical alias rejection.
- Python emitted the wrong diagnostic ID for one canonical-alias path because `detail_code` was passed positionally.
- Public dependency nominal types could make ABI text depend on a local alias.
- Method declaration reordering initially changed ABI unnecessarily.
- Build hash verification was initially absent.
- Interface writes initially lacked the final atomic/symlink safety contract.
- Go initially attached fresh SMI metadata but still rechecked source instead of consuming the interface surface.
- Entry module directives were initially stripped before entry public-surface validation.
- Generated mobile Standard Core runtime initially failed to compile after `SourceModuleStmt` gained an interface pointer.
- Standard standalone bundle initially flattened module source files, causing a build to succeed but runtime namespace lookup to fail (`SAGA-T102`). It now embeds a virtual source graph and reconstructs module boundaries.

## Evidence summary before source-manifest binding

- Python non-platform unittest inventory: **334 / 334 PASS**.
- Platform/Evidence unittest inventory: **9 / 9 PASS** after source-manifest binding.
- Combined Python unittest inventory: **343 / 343 PASS**.
- Python Natural Module Core dedicated tests: **18 / 18 PASS**.
- Go implementation: `go test ./...` PASS.
- Python Self Conformance: **44 / 44 PASS**.
- Go Self Conformance: **44 / 44 PASS**.
- Cross-implementation module graph conformance: **12 / 12 PASS**.
- Parser/expression fuzz: **125,000 cases, 0 unexpected host exceptions**.
- Formatter smoke: **39 standalone-compilable example programs round-trip + idempotence PASS**.
- 61-module SMI smoke graph: Python/Go ABI and build hashes matched.
- Standard standalone namespaced module example: execution PASS.
- Generated mobile Standard Core namespaced module example: Go execution test PASS.

## Claim boundary

These are project-executed tests. They are not independent third-party certification. Physical-device, platform, security and GA evidence remain governed by their own qualification artifacts.
