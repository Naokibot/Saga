# Saga 0.20.0 Validation Report

Validation host: Linux x86-64. Primary scope: official `saga-sh3` SH-3
all-source self-hosting qualification.

## SH-3 qualification

| Check | Result |
|---|---:|
| C11 bootstrap VM strict build (`-pedantic -Wall -Wextra -Werror`) | PASS |
| C11 launcher strict build | PASS |
| Stage1 -> Stage2 compiler rebuild | PASS |
| Stage2 -> Stage3 compiler rebuild | PASS |
| Stage2 == Stage3 | PASS |
| Stage2/Stage3 canonical kernel lowering equality | PASS |
| Standard Core success corpus | **23/23 PASS** |
| Standard Core diagnostics | **11/11 PASS** |
| Edition 2027 Preview via SH-3 kernel | **14/14 PASS** |
| source-unit loader | PASS |
| deterministic SH3IMG1 lowering | PASS |
| lowered image execution | PASS |
| empty-PATH official `saga` execution | PASS |
| empty-PATH official `sagac` execution | PASS |
| non-Saga bootstrap source-boundary audit | PASS, 0 problems |

Compiler Stage2/Stage3 SHA-256:
`a905fc8e834f2f2bd45a8698d737590e1ce5f0d9a9b5d03f64bb3eb020fa951b`

Canonical kernel image SHA-256:
`e9d03804ccd36c7ffaecb709cf95799cd4de17bf62b0667d28d9d7b8b417b261`

## Sanitizer and robustness

- ASan/UBSan valid corpus: **48/48 PASS** with leak detection enabled.
- Malformed bytecode fuzz: **500/500 controlled failures**, zero timeouts,
  zero ASan/UBSan memory-corruption findings. Leak checking is not used for the
  malformed fatal-exit fuzz because those paths terminate immediately; valid
  program runs were checked with LeakSanitizer.
- A malformed-hex allocation ordering issue found during review was repaired.

## Reference implementation regression

- Go reference unit tests: PASS.
- Go `vet`: PASS.
- Go Race Detector: PASS.
- Python reference: **155/155 PASS + 4 subtests**.
- Native game checker/runtime/manifest: **92/92 aligned**.
- Hosted API exhaustive validator: PASS; hardware/external adapters retain the
  documented test-double limitations.
- Internal automated security review: PASS, 0 unresolved findings; this is not a
  third-party security certification.

## Distribution check

The Linux x86-64 official SH-3 `saga` launcher and `sh3vm` bootstrap machine are
statically linked. They run with `PATH=/nonexistent`. No Go, Python, Java, Node,
Rust or other programming-language runtime/compiler is part of the official SH-3
runtime distribution.

## Limits of this evidence

SH-3 is a language implementation/source property, not a claim that optional OS,
GPU, FFI vendor shims or third-party libraries are all Saga source. The official
SH-3 binary in this report was executed on Linux x86-64; Windows/macOS SH-3
binary target execution is not claimed by this report.
