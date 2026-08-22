# Saga 0.10.0 release notes

Saga 0.10.0 is a correctness and security review patch for the Saga 0.9 language edition.

## Fixed

- Remapped global Saga objects when creating isolated thread-task snapshots. This removes host `RLock`/executor-copy failures and restores the specified task isolation semantics.
- Prevented `private` fields from leaking through `print(...)` and `text(...)`.
- Defined numeric literal digits as ASCII `0`-`9` and aligned Python and Go behavior.
- Disabled ambient proxy inheritance and automatic redirects in the WebSocket adapter so network capabilities cannot be bypassed by library-internal routing.
- Removed the legacy 16 MiB external-process output rejection that contradicted Saga's no-fixed-normative-ceiling policy. Host memory remains the practical resource constraint.
- Changed canonical `.sagapkg` members to ZIP `STORED` for deterministic bytes across zlib implementations.

The language edition remains Saga 0.9; this patch changes the reference implementations and packaging profile without adding a new source-language edition.
