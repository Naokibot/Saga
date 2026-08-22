# Saga 0.12 Native Independence Profile

Saga 0.12 changes the default distribution model from a Python-hosted reference
implementation to a self-contained native implementation.

## Normative deployment property

A conforming **Saga Native Distribution**:

1. MUST provide a `saga` executable that can lex, parse, type-check and execute
   Saga Standard Core programs without invoking another language runtime.
2. MUST NOT require Python, Go, Java, JavaScript/Node, Ruby, .NET, a JVM, clang,
   GCC or another programming-language toolchain for normal execution.
3. MUST provide `saga build` for host-native standalone application bundles
   without invoking another compiler or language runtime.
4. MUST verify the SHA-256 hash of a standalone bundle before executing its
   embedded Saga payload.
5. MUST report implementation/runtime dependency metadata through `saga info`.

The Linux reference native binary is built with `CGO_ENABLED=0` and is
statically linked. Windows distributions are PE executables and do not require
Go or Python to be installed.

## Bootstrap boundary

No programming language implementation can be created from literal nothing: a
first executable must be produced by some existing machine-code path. Saga
therefore distinguishes:

- **bootstrap provenance**: the audited seed implementation used to produce the
  native compiler/runtime binary;
- **language/runtime dependency**: software required on an end-user machine to
  compile and run Saga programs.

Saga 0.12 eliminates the second category for Standard Core. The current seed
source is retained under `implementations/go/` solely as a bootstrap and
independent-conformance implementation. It is not a runtime prerequisite.

## Python reference implementation

The Python implementation remains in the source distribution only for:

- differential conformance testing;
- diagnostic and hosted-library experimentation;
- migration compatibility.

It is not installed by the normal Saga Native installer and is not part of the
runtime dependency closure of a compiled Saga program.
