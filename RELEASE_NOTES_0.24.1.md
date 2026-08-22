# Saga 0.24.1 — Review and Correctness Patch

Saga 0.24.1 is a patch release over 0.24.0. It keeps Language Edition 1.0 RC1, Edition 2027 Preview, SH-3 self-hosting, Universal App Actions, the Browser Host profile, game profiles and the Defensive Cybersecurity Profile while fixing defects discovered during a full source review and end-to-end revalidation.

## Correctness and security fixes

- Fixed cross-process DB writes through symlink aliases so persistence always targets the canonical database file instead of replacing the symlink itself.
- Fixed the Python reference implementation's `security.file_sha256`, `cidr_contains`, `certificate_info` and `tls_probe` signatures and runtime values to match their declared `result[T,E]` contracts.
- Fixed Python native return validation and task/process snapshot handling for `ResultValue`.
- Made Universal App JSON reject duplicate object keys instead of silently accepting last-key-wins ambiguity.
- Bounded the Universal App `filesystem.read_text` host action and rejected invalid UTF-8.
- Rejected invalid UTF-8 HTTP server request bodies and CR/LF injection in response Content-Type values.
- Added explicit, optional administrator policies for standard HTTP timeout/body size and process output size without reintroducing forbidden fixed language-level resource ceilings.
- Hardened the Go registry client/extractor against mismatched package identities, unescaped search text, oversized wire/package data, duplicate archive paths, unsupported file types, excessive extracted file counts and archive expansion attacks.
- Hardened the Python reference registry with package/metadata limits, stricter package name/SemVer validation, archive traversal/symlink/file-count/expansion checks and cleanup after failed extraction.
- Updated Hosted API validation to the current `result[T,E]` security contract.
- Removed a duplicate publisher-fingerprint verification branch in the Python registry server.

## Regression caught during the review

An initial hardening change imposed an 8 MiB fixed cap on standard `process.run` output. The existing 17 MiB regression test correctly failed because Saga 1.0 forbids arbitrary fixed normative resource ceilings. The change was replaced with an optional deployment policy (`SAGA_PROCESS_OUTPUT_LIMIT_BYTES`). Standard HTTP limits follow the same model. This preserves language semantics while allowing production operators to enforce host budgets.

## Validation summary

- Python reference: **161/161 collected tests PASS** across 15 independently executed test modules.
- Go Native: full tests PASS, `go vet` PASS, Race Detector PASS.
- Optional Go profiles: `sagaffi`, `sagajit`, combined FFI+JIT, `sagadesktop`, `sagadesktop+sagavulkan` tagged suites PASS.
- Defensive security APIs: 11 `security` functions + 8 crypto extensions PASS.
- Hosted APIs: **160/160** functions across 28 modules exercised.
- Native game API: **101/101** aligned.
- Browser Host API: **101/101** PASS.
- Universal App Action API: 10 source APIs / 53 browser operation identifiers PASS.
- Real Chromium 144 Blink/V8: PASS.
- Parser fuzz: 100,000 cases; expression fuzz: 25,000 cases; 0 unexpected host exceptions.
- Machine smoke: exact arithmetic, file/SQLite, TCP, UDP, AES-GCM, process, WebSocket, image, video and Othello PASS.
- SH-3 split qualification: compiler and kernel fixed points PASS; Standard Core 23/23; diagnostics 11/11; Edition 2027 15/15; source loader/image/empty-PATH/audit PASS.
- Linux x86-64 Native binary executes and is statically linked. Linux ARM64, Windows x86-64/ARM64 and macOS x86-64/ARM64 portable binaries cross-build and format-check successfully.
- Desktop OpenGL/window/shader/audio integration PASS under Xvfb with SDL dummy audio. Vulkan loader/device probing executes, but a usable Vulkan instance/device path is not available on this host (`create_instance=-9`), so real Vulkan rendering is not claimed.

## External evidence boundaries

AWS account, physical GPIO, Spark runtime and pygame paths use documented test doubles when unavailable. Android/iOS store/device qualification, Windows/macOS target-host execution, physical GPU/gamepad validation, vendor-service qualification, independent penetration testing and third-party conformance certification remain external evidence gates.
