# Saga 0.12.0 review report

## Goal

Make Saga usable as an operationally independent programming language: normal
installation, execution, type checking, packaging and host-native standalone
application creation must not require another programming-language runtime or
compiler toolchain on the user machine.

## Findings from 0.11

1. The default installer created a Python virtual environment and therefore
   made Python 3.13 an operational dependency.
2. Standard-profile native builds invoked the Go toolchain.
3. The normal command surface treated the Python implementation as primary and
   the native Go implementation as a secondary implementation.
4. The installer bundled both a Python wheel and native implementation, so the
   runtime dependency closure was larger than the language semantics required.
5. `collectSourceFiles` did not resolve `pkg:` imports consistently with the
   loader, which could make project locking/build collection diverge from
   execution.
6. The Python runtime-AOT helper assumed the old one-line Go `main` function and
   stopped embedding source after the native main function became structured.

## Corrections

- Promoted the independent statically linked implementation to **Saga Native**.
- Added native `saga build` that creates a standalone executable by appending a
  canonical SHA-256-authenticated Saga project payload to the native runtime.
- Removed Python/Go/clang prerequisite checks and Python virtual-environment
  creation from the normal native installer.
- Native installer now embeds only the matching Saga Native binary, verifies its
  hash, runs native self-conformance, and records zero language-runtime
  dependencies.
- Added `runtime_dependencies: []`, `compiler_toolchain_required: false`, and
  bootstrap provenance fields to `saga info`.
- Fixed source collection for `pkg:` imports.
- Made the legacy Python Standard-bundle helper resilient to the structured
  Saga Native `main` implementation.
- Added a language-neutral standalone bundle format (`SAGABND2`).
- Added Native Independence, Bootstrap Trust and Native Distribution Profile
  specifications.

## Important scope distinction

Saga 0.12 eliminates *end-user language-runtime/toolchain dependencies* for the
Standard Core and standalone host-native applications. The current native seed
source is still written in Go. That is bootstrap provenance, not a requirement
for running or compiling Saga after installation. A fully source-self-hosted
front end remains a future bootstrap-hardening milestone and is not falsely
claimed here.
