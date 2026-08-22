# Saga Native Distribution Profile 1.0 — Final Candidate

This profile specifies deployment requirements for an implementation that may
call itself **Saga Native**.

## Required commands

`run`, `check`, `build`, `lock`, `verify`, `pack`, `conformance`, `info`.

## Runtime independence

The commands above shall be executable without a separately installed
programming-language runtime or compiler toolchain.

## Standalone application format

A standalone Saga application consists of a native Saga runtime followed by:

1. canonical UTF-8 JSON payload (`schema = 2`);
2. 8-byte magic `SAGABND2`;
3. unsigned little-endian 64-bit payload length;
4. 32-byte SHA-256 payload digest.

The payload contains an entry path and a map of project-relative source files.
An implementation shall verify path confinement and payload digest before
execution.

## Conformance

`saga info` shall expose `runtime_dependencies: []` and
`compiler_toolchain_required: false` for this profile. `saga conformance --json`
shall return a machine-readable pass/fail report based on stable diagnostic IDs,
not localized message text.
