# Saga 0.6.0 Release Notes

Saga 0.6.0 is the standardization-readiness release.

## Added

- `saga standards` evidence and governance registry.
- Independent Go implementation of the common core profile.
- Differential conformance runner shared by Python and Go.
- Formal isolated-task memory model with Send-value enforcement.
- Unicode 15.1 XID identifier profile, NFC enforcement and bidi-control rejection.
- Compatibility snapshots and removal checker.
- Native offline installers for Linux x86-64/ARM64 and Windows x86-64/ARM64.
- Independent laboratory handoff package.

## Correctness and safety changes

- Python 3.13 and Unicode 15.1 are required for the normative Python implementation.
- Spawned tasks receive structural snapshots and cannot share native resources.
- Non-NFC identifiers are rejected rather than normalized silently.
- Source bidi controls outside comments and strings are rejected.

## Compatibility

This is a minor-version preview release. Hosted APIs remain provided by the Python implementation; the Go implementation currently covers the language core used by the conformance profile.
