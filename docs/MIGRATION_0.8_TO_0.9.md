# Migrating Saga 0.8 to 0.9

Most valid Standard Core 0.8 source remains source-compatible with 0.9. The principal changes are tooling and internationalization semantics.

1. Set `language = "0.9"` in `saga.toml` after running the 0.9 test suite.
2. Stop matching diagnostic prose. Consume category `code`, detailed `id`, exit status, and source range.
3. Use diagnostic schema 2 for machine integrations. SARIF 2.1.0 is available for CI/code review.
4. Project names may now contain NFC Unicode XID components separated by hyphens. Existing ASCII names remain valid.
5. Invalid UTF-8 is now a lexical diagnostic (`SAGA-L104`) rather than a generic file/parser failure.
6. Non-NFC identifiers (`SAGA-L105`) and bidi controls outside strings (`SAGA-L106`) have dedicated diagnostic IDs.
7. No fixed project-name-length rule exists in 0.9; host storage limits are implementation characteristics.

Use `saga check . --standard`, `saga test .`, `saga lock`, and `saga verify` before repackaging.
