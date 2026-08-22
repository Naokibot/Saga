# Saga 0.26.2 alternate-perspective review report

## Review perspective

This pass reviewed Saga 0.26.1 as a package/install/build system rather than primarily as a GA-evidence system. The main questions were:

1. Can a dependency change after a successful signed install and still execute?
2. Can a Registry store a package that its own clients later reject?
3. Can concurrent `add` operations lose state?
4. Can an interrupted pack/build destroy a previous valid artifact?
5. Can an output path overwrite an input through direct or symlink aliases?
6. Does an incremental cache validate the artifact it is reusing?
7. Do Python and Go interpret the same arithmetic and lock/package edge cases identically?

## Findings and corrections

### High — post-install dependency modification executed through `pkg:`

0.26.1 recorded the downloaded package SHA-256 but `pkg:` source loading did not re-anchor installed files to that artifact. A reproduced test changed an installed dependency from `x*2` to `x*99`; the modified code executed. Python and Go now validate the installed lock, required member and reconstructed canonical package SHA-256 against the dependency record on import. Modified, relocked or untracked dependency code fails closed.

### High — Registry accepted signed archives inconsistent with `saga.lock`

The server checked identity/signature but could persist an archive whose member bytes disagreed with its lock. Both Registry implementations now verify every tracked member's path, size and SHA-256, reject missing/extra members and reject non-canonical archive aliases before storing the package.

### High — concurrent package additions could lose dependency records

Two package additions could read the same old dependency manifest and last-writer-wins one another. Final target placement plus dependency-manifest update is now serialized with a project-level cross-process lock; the manifest is re-read while locked and committed atomically.

### High — pack/build output could overwrite inputs

`pack -o` and build output paths could be directed at source/manifest/runtime/compiler inputs. Go pack also had a parent-symlink alias bypass. Python/Go pack, Python AOT/Standard bundle and Go standalone now reject canonical-path collisions before writing.

### Medium/high — standalone cache trusted a modified output

The old cache key covered source/runtime inputs but not the built file. Cache v2 stores the built executable SHA-256 and verifies it before a HIT. A modified output triggers a rebuild.

### Medium/high — pack verification/write TOCTOU

A lock could validate and a source change before ZIP emission, yielding a successful package inconsistent with its own lock. Pack now captures one lock snapshot and rechecks each emitted member against the snapshot immediately before writing. The Go local lock parser is also strict against duplicate JSON keys.

### Medium — failed writes could truncate previous artifacts

Lock/package/build outputs now use same-directory temporary files and atomic replacement in the reviewed paths. Regression tests inject write/compiler failures and confirm the previous artifact remains unchanged.

### Medium — non-canonical ZIP member aliases

Package paths such as `./a.saga` or `a//b.saga` can be interpreted differently by ZIP tooling. Python and Go now require canonical POSIX member names in addition to traversal/symlink/size checks.

### Medium — negative remainder semantics differed across implementations

Python's `%` uses floor-based modulo while Go/C/WASM signed remainder uses truncation toward zero. The specification now defines truncating integer remainder. The Python interpreter and Python transpilation target were corrected, and the differential conformance corpus now contains the negative-operand case.

## Review result

All findings reproduced in this pass have corrections and regression coverage in the 0.26.2 candidate. This is still a project-internal review, not an independent audit. External GA evidence remains external and is not simulated as passing.
