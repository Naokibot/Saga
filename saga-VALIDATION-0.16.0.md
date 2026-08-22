# Saga 0.16.0 validation report

Validation host: Debian GNU/Linux 13 x86-64.

## Passed on this host
- Python reference regression: **155/155 PASS + 4 subtests PASS**.
- Saga Native `go test ./...`: **PASS**.
- `go vet ./...`: **PASS**.
- Go Race Detector: **PASS**.
- Native game API checker/runtime/manifest: **91/91 aligned**.
- Portable Shader IR SIR1 parser/codegen unit tests: **PASS** for GLSL 1.20, GLSL 4.50, HLSL 5, MSL 2 and WGSL generation.
- SIR1 -> generated GLSL -> real OpenGL shader compilation/present: **PASS**.
- Existing SDL2/OpenGL desktop path: **PASS** under Xvfb.
- Native2 second presentation backend using SDL accelerated renderer: **PASS** (`renderer=opengl`, accelerated=true on this host).
- Desktop game smoke: **PASS**; Mesa llvmpipe/OpenGL 4.5/GLSL 4.50.
- Physical gamepad harness execution: **executed but BLOCKED**, controller count 0.
- Vulkan loader probe: loader 1.4.309 found; **full Vulkan gate BLOCKED** because no usable ICD was installed and instance creation returned `-9`.
- Technical implementation-independence static audit: **PASS**, no Python-runtime invocation/import dependency detected in Native source set.
- Portable differential suite using current binaries: **14/14 PASS**.
- Extended Standard Core cross-implementation subset: **10/10 PASS**, including the result-type defect found and fixed during this review.
- Third-party lab runner internal kit smoke: **14/14 PASS**, deliberately labeled non-third-party.
- Signed package registry localhost E2E: **health -> publish -> search -> trust -> add -> verify PASS**.
- Registry native TLS mode with self-signed test certificate: **PASS**.
- Internal automated security audit: **PASS, 0 unresolved high/critical findings**; not a third-party audit.

## Defects found and fixed
1. Python reference checker used `RESULT(...)` but failed to import it, causing an internal error for explicit `result[T,E]` annotations. Import and regression test added.
2. Native CLI returned BSD-style 65/67/68 codes for language diagnostics while the 1.0 RC1 specification requires lexical=2, syntax=3, type=4, runtime=5. Native exit mapping corrected.
3. Differential/lab tools still checked legacy diagnostic category strings instead of stable diagnostic IDs. They now prefer `diagnostic_id`.
4. Release/LSP version metadata and tests were updated consistently to 0.16.0.

## External gates not claimed as passed
See `validation/external-gates-0.16.0.json`. Windows real-host Direct3D, macOS real-host Metal, physical gamepad, physical GPU, full Vulkan swapchain/present, organizationally independent implementation, independent lab certification and a public Internet registry require external evidence.
