# Saga 0.10.0 review report

## Scope

Saga Python reference implementation, independent Saga Go Standard Core implementation, parser/type/runtime semantics, diagnostics, plugin and processor boundaries, OS sandboxing, project/package tooling, installers and cross-platform release artifacts.

## Corrected issues

| Severity | Finding | Correction |
|---|---|---|
| High | Python plugins executed in-process and could bypass Saga capabilities using Python APIs. | Plugins now execute in separate isolated workers; Linux strict mode adds OS namespaces/mount masking; serialized value boundary and restricted builtins/AST policy added. |
| High | Raw allowed Python modules could expose ambient objects such as `statistics.sys`. | Replaced raw module exposure with narrow read-only facades. |
| High | Dunder/object-graph introspection could be used as a Python sandbox escape technique. | Import/dunder AST paths rejected before isolated worker execution. |
| High | “Strict” isolation could otherwise degrade silently on unsupported hosts. | Strict sandbox is fail-closed when the required strong OS mechanism is unavailable. |
| High | Go implementation stopped at PCL1. | Rebuilt as an independent Standard Core implementation: exact numbers, control flow, functions, generics, collections, option, OOP/interfaces/abstract classes, exceptions, tasks, source units, type checking, lock/verify/pack and structured diagnostics. |
| Medium | Go project source boundary could traverse a symlinked directory component. | Every component in locked source paths is checked; symlink traversal is rejected. |
| Medium | Diagnostic detail classification still had paths that could depend on localized prose. | Detailed diagnostic IDs are carried explicitly as structured exception/diagnostic data; localization is rendering only. |
| Medium | Windows could fail importing the sandbox module because of unconditional Unix `resource` import. | Platform import made conditional; unsupported strong sandbox mode now reports a controlled refusal. |
| Medium | `saga verify` registered its path argument twice. | Removed duplicate argument and added regression coverage. |
| Medium | Hosted general-purpose support lacked built-in regex/system facades. | Added capability-neutral `regex` and `system` modules. |
| Medium | Second implementation packaging could differ from the reference implementation. | Go canonical lock/package implementation now produces byte-identical lock data and `.sagapkg` for tested projects. |

## Current assessment

No known critical defect was left intentionally unresolved in Standard Core during this review. This is not a proof of defect absence and not an independent security certification. Remaining external validation gates are documented in the validation and audit handoff files.
