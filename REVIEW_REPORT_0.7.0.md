# Saga language review report — 0.8.0

Date: 2026-08-07  
Scope: language specification, Python reference implementation, Go PCL1 implementation, standard library boundaries, project/package tooling, conformance tooling, and native installers.

## Executive result

Saga 0.8.0 is materially more suitable for international-standard review than 0.6.0. The review converted several host-dependent or ambiguous outcomes into normative Saga behavior, added reproducible source packaging and source-unit semantics, aligned two implementations on a declared common profile, and added stable machine interfaces for diagnostics and conformance.

It remains an International Standard candidate, not an ISO/IEC standard. External proposal, committee, adoption, expert, and independent-laboratory requirements remain open.

## Corrected findings

| Severity | Finding in 0.6 | Correction in 0.7 | Verification |
|---|---|---|---|
| Critical | Cyclic class-instance equality could leak Python `RecursionError` | Class equality is identity equality; collection equality is cycle-aware | object cycle regression test |
| High | Deeply nested syntax could leak a host recursion failure | normative nesting ceiling and `SAGA-P002` | 3,000-level nesting test |
| High | Decimal overflow could leak `decimal.Overflow` and bypass Saga catch | arithmetic host exceptions are translated to Saga errors/resource diagnostics | catchable overflow test |
| High | `task.submit` and `task.parallel_map` bypassed the Send boundary | all task submission APIs validate arguments; task results are also Send-checked | native-resource argument/result tests |
| High | Task-returned class instances retained the isolated interpreter's class object | cross-task snapshot remaps instances to the receiving interpreter | returned object method test |
| High | Project names could contain path separators and influence default package output | normative project-name syntax | path-escape regression test |
| High | Custom-prefix installers still wrote launchers to the global user launcher directory, so `--prefix`/`--no-path` were misleading and uninstall scope could cross installations | custom prefixes now own `<prefix>/bin`; receipts, direct-run instructions, and uninstall use the same resolved launcher directory | installer unit test plus isolated install/uninstall |
| High | Source graph had no standard multi-file semantics | `use "relative.saga"`, cycle/root/symlink checks, deterministic dependency order | source-unit tests |
| Medium | `0.1.0` was rejected by an incorrect SemVer expression | corrected SemVer 2.0-compatible validation | zero-major project test |
| Medium | Identifier membership depended on the host Unicode database | vendored Unicode 15.1 XID tables in Python and Go | Unicode tests and differential cases |
| Medium | JSON on cyclic public object graphs produced an implementation recursion message | explicit cyclic-reference and depth diagnostics | JSON cycle test |
| Medium | CLI returned one generic failure status | stable lexical/syntax/type/runtime/resource/input/internal statuses | subprocess exit-code test |
| Medium | Diagnostics were difficult for IDE/CI integration | JSON diagnostic schema 1 | JSON diagnostic test |
| Medium | Local builds had no source integrity lock | `saga.lock` schema 1 and `saga verify` | mutation-detection test |
| Medium | Packages were not reproducible | deterministic `.sagapkg` order, time, mode, and compression | byte-identical double-pack test |
| Medium | Go PCL1 failures did not match standard exit statuses | stage-specific Go statuses and diagnostic codes | 13/13 differential suite |
| Medium | Standard project templates violated their own `--standard` lint profile by exposing `any` and an untyped callback | exported canonical opaque resource types and explicit `unit` callback result; all nine templates now pass standard checks | template conformance checks |
| Low | Host Unicode version was needlessly fixed to exactly Python 3.13's database | Python 3.13+ supported with vendored membership profile | clean-wheel and installer checks |

## Specification upgrades

- clause-structured working draft with scope, references, terms, conformance, lexical rules, source units, type system, values, exact numbers, collections, evaluation order, functions, OOP, exceptions, option, memory model, hosted capabilities, diagnostics, limits, and annexes;
- normative `spec/saga-0.7.ebnf`;
- PCL1, Standard Core, and Hosted Standard conformance profiles;
- specified evaluation order and right-associative exponentiation;
- object identity and collection structural equality separated;
- no undefined behavior category; implementation-defined and unspecified outcomes are bounded;
- source units, manifest edition, lock schema, and deterministic package format;
- stable diagnostics and CLI exit-status profile;
- task argument and result snapshot semantics with happens-before rules.

## Open technical findings

The following do not invalidate the 0.7 candidate but block a mature 1.0 standard claim:

1. Go implements PCL1, not complete Standard Core.
2. Source units share one namespace; namespace imports, exports, and separately compiled interfaces are not standardized.
3. Third-party dependency solving, signed package metadata, and a public registry are not implemented.
4. Generic constraints, variance, and binary compatibility are not defined.
5. Task cancellation, fairness, structured concurrency, and async I/O are not standardized.
6. There is no native compiler, stable ABI, debugger protocol, or language-server protocol implementation.
7. Hosted modules require wider Windows, macOS, ARM64, mobile, cloud, cluster, and hardware validation.
8. Plugins and annotation processors remain trusted host-code boundaries.
9. Independent security review, independent conformance testing, and formal standards editorial review have not occurred.

## Recommendation

Treat 0.7 as a public Working Draft / Committee Draft candidate for technical review. Do not label it ISO-approved, ISO-certified, or an International Standard. Prioritize a complete independent Standard Core implementation and external review before freezing 1.0 semantics.
