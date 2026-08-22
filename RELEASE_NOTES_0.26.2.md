# Saga 0.26.2 release notes

## Theme: package/install/build durability and cross-implementation semantic consistency

Saga 0.26.2 is a review-hardening patch built from the 0.26.1 independent-review candidate. This review deliberately changed perspective: instead of rechecking the GA evidence chain first, it treated package installation, local build outputs, interrupted writes, concurrent package operations, damaged archives and cross-implementation arithmetic semantics as the primary attack/failure surface.

Saga 0.26.2 is still pre-GA. Independent Final-spec approval, native Windows/macOS execution evidence, a live public HTTPS Registry run and an independent signed security audit remain external GA gates.

## Defects corrected

- Installed `pkg:` dependencies are re-anchored at runtime to the SHA-256 of the originally downloaded/signed `.sagapkg`. Editing the installed source, refreshing its local lock, adding an untracked source or injecting duplicate dependency-lock keys fails closed instead of executing altered code.
- Python and Go Registry servers validate the entire incoming `saga.lock` snapshot against archive member bytes before accepting a publication. Signed but internally inconsistent archives are rejected at publish time rather than being stored for clients to discover later.
- Registry archive paths must be canonical POSIX package paths. Alias spellings such as `./a.saga` or `a//b.saga`, traversal, backslashes, duplicate normalized names, symlinks and special files are rejected.
- Concurrent package additions are serialized at the project commit boundary so two `saga add` operations cannot lose each other's dependency records. Trust-store updates are similarly serialized.
- `saga.lock`, package archives and dependency metadata use same-directory temporary files, fsync and atomic replacement where applicable; failed package writes preserve a previous valid artifact.
- `saga pack -o` cannot overwrite a tracked project input. Go also resolves existing targets and symlinked parent directories so an alias path cannot bypass the collision check.
- Packaging now rechecks each member's size and SHA-256 while emitting the archive and embeds the single lock snapshot it validated. A source or lock change between the initial check and archive write is rejected instead of yielding a successful inconsistent package.
- Go local lock verification now rejects duplicate JSON keys, matching the strict Python/Registry behavior.
- Native standalone builds write to a same-directory temporary executable and atomically replace the destination. Output and cache paths cannot overwrite source inputs, dependency metadata or the runtime template.
- Native incremental build cache v2 binds both the input/runtime cache key and the SHA-256 of the generated executable. A post-build modified executable is a cache miss and is rebuilt.
- Python AOT and Standard Core bundles reject output paths that collide with source inputs or the compiler executable (`clang`/`go`), and compiler failure preserves a previous valid output.
- The `%` operator had a real Python-reference/Go-Native difference for negative integers. Saga now normatively defines integer remainder using a quotient truncated toward zero. Python reference, Go Native, C/WASM/bare-metal behavior and the Python transpilation target are aligned; `-2 % 7 == -2`, `7 % -3 == 1`.

## Compatibility

The language surface is unchanged except that previously inconsistent negative-integer remainder behavior is now specified and cross-implementation consistent. Package/archive handling is intentionally stricter: non-canonical or internally inconsistent package files that older builds could accept are rejected.
