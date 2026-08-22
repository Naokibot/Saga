# Saga 0.13.0 — validation report

## Core implementation

| Validation | Result |
|---|---:|
| Python unit/regression suite | 154 / 154 PASS |
| Python Standard Core suite | 154 / 154 PASS |
| Saga Native self-conformance | 13 / 13 PASS |
| Python <-> Native observable cross-suite | 35 / 35 PASS |
| Go unit tests | PASS |
| Go vet | PASS |
| Go Race Detector | PASS |
| Learning examples | 8 / 8 check PASS |
| Hosted reference API coverage | 149 / 149 entry points exercised |

## Robustness

| Validation | Result |
|---|---:|
| Random parser inputs | 100,000 |
| Random expression executions | 25,000 |
| Unexpected host exceptions in fuzz run | 0 |
| Internal automated security review | PASS, 0 unresolved findings |

The internal security review is project-generated evidence, not an independent
third-party audit.

## Self-hosting

| Validation | Result |
|---|---:|
| Stage1 compiler generated from `sagac.saga` | PASS |
| Stage1 -> Stage2 | PASS |
| Stage2 -> Stage3 | PASS |
| Stage2 vs Stage3 byte comparison | IDENTICAL |
| Stage2 SHA-256 | `efade3e00f804b0ec49e3c5b2446d4ea2cb9d60212775a2852a0d24e1cfaeabf` |
| Stage3 SHA-256 | `efade3e00f804b0ec49e3c5b2446d4ea2cb9d60212775a2852a0d24e1cfaeabf` |

## Native installed workflow (Linux x86-64)

The final native installer was run into an isolated prefix. The installed
workflow passed:

1. payload hash verification;
2. on-target Stage1 -> Stage2 -> Stage3 fixed-point self-host bootstrap;
3. Native self-conformance 13/13;
4. `fmt`;
5. `lint --standard --deny-warnings`;
6. `check`;
7. self-hosted `sagac` standalone build;
8. standalone execution with a nonexistent PATH;
9. REPL state preservation;
10. uninstall.

The test application used generic interface binding and a stateful lexical
closure and printed exactly:

```text
41
42
```

## Determinism

Two standalone builds from the same source were byte-identical in the
reproducibility check. The self-host compiler fixed-point build was also
byte-identical at Stage2 and Stage3.

## Native binary formats

- Linux x86-64: static ELF x86-64;
- Linux ARM64: static ELF AArch64;
- Windows x86-64: PE32+ x86-64;
- Windows ARM64: PE32+ ARM64.

`ldd` on the final Linux x86-64 Native runtime reports `not a dynamic executable`.

Windows and ARM64 target execution was not performed on this Linux x86-64 host;
cross-compilation and binary-format validation are not described as target-device
validation.
