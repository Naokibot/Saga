# Saga 0.20.0 Release Notes

Saga 0.20.0 completes the SH-3 all-source self-hosting milestone for the official
`saga-sh3` implementation.

## SH-3 completion

- Canonical bootstrap compiler/lowering is Saga source: `selfhost/sh3/sh3c.saga`.
- Canonical lexer/parser/static checker/runtime/built-ins/source loader/user
  lowering is Saga source: `selfhost/sh3/kernel.saga`.
- The only non-Saga official bootstrap code is the published C11 generic VM and
  launcher. They contain no Saga grammar/type/runtime policy.
- Stage1 -> Stage2 -> Stage3 compiler rebuild reaches a byte-identical fixed point.
- Stage2 and Stage3 compile the canonical Saga kernel to byte-identical output.
- Standard Core corpus passes 23/23 success cases and 11/11 diagnostic cases.
- Edition 2027 Preview passes 14/14 through the canonical SH-3 kernel.
- Empty-PATH official runtime and self-host compiler execution pass.

## Defects found and repaired during SH-3 completion

- class associated-type parsing could run past `;`/`}` and hang;
- `await` failed to unwrap actor/task futures;
- compute-reference lowering called a stale helper name and mixed exact IR
  constants into float data without explicit flavor normalization;
- malformed bootstrap hex input allocated before complete validation.

## Bootstrap hardening

- strict ISO C11 `-pedantic -Wall -Wextra -Werror` build passes;
- Linux x86-64 official `saga`, `sagac` and `sh3vm` are statically linked;
- ASan/UBSan valid-language corpus: 48/48 with no sanitizer findings;
- malformed-bytecode memory-safety fuzz: 500 cases, zero timeouts, zero
  ASan/UBSan corruption findings.

Go and Python implementations remain in the source tree as explicitly
non-official reference implementations for differential testing and portability.
