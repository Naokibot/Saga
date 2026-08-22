# Saga 0.9 Language Server

Start the dependency-free stdio language server with:

```bash
saga lsp --language en
```

Implemented protocol surface:

- `initialize` / `initialized`;
- `shutdown` / `exit`;
- `textDocument/didOpen`;
- full-sync `textDocument/didChange`;
- `textDocument/didSave`;
- `textDocument/didClose`;
- `textDocument/publishDiagnostics`.

The server intentionally reuses the compiler diagnostic catalogue. LSP `code` is the detailed Saga diagnostic ID (for example `SAGA-T101`), while `data.category` contains the stable broad phase category (`SAGA-T001`). LSP ranges are zero-based as required by editor protocols; Saga CLI/JSON source ranges remain one-based according to the Saga CLI specification.

This first language-server profile is diagnostic-focused. Completion, go-to-definition, rename, semantic tokens, formatting edits, and workspace-wide multi-file incremental analysis are future tooling work and are not required by the Saga 0.9 language semantics.
