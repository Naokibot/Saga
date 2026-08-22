# Saga 0.10 threat model

## Security boundaries

1. Saga source is untrusted input to lexer/parser/checker/runtime.
2. Hosted effects are capability-gated (file, network, DB, process, UI, plugin, environment/cloud).
3. Python plugins and safe annotation processors are untrusted extension code. On Linux they run in a separate interpreter with `-I -S`, a minimal environment, user/mount/PID/IPC/UTS/network namespaces, masked sensitive filesystem trees, `no_new_privs`, resource limits, restricted builtins, AST anti-introspection rules, and JSON-only value transfer.
4. Standard Core task boundaries copy Send values and do not share native resources.
5. CPU parallel workers are isolated processes and inherit no Saga hosted capabilities.
6. The Go implementation is an independent Standard Core implementation and does not call Python.

## Primary threats

- parser/interpreter crashes or host traceback leakage;
- path traversal and symlink escape;
- SSRF / redirect / proxy bypass;
- shell injection and process capability escalation;
- plugin breakout through imports, Python object introspection, ambient modules, filesystem, network, or inherited environment;
- private-field disclosure through display/reflection/serialization;
- task data races or native-resource sharing;
- diagnostic/conformance dependence on localized prose;
- package tampering or non-reproducible build output;
- Unicode source confusion and bidi controls.

## Residual risks

- The Python language is not itself a security sandbox; isolation depends primarily on the Linux OS boundary. A kernel vulnerability can invalidate that boundary.
- Strict plugin execution is fail-closed on platforms where the strong OS sandbox is not implemented. This release does not claim an AppContainer-equivalent Windows plugin sandbox.
- Optional third-party libraries (Pillow/OpenCV/Pygame/cloud/Spark etc.) have their own vulnerability surface and are outside Standard Core.
- Administrator-granted `--allow-process` can run arbitrary executables by design.
