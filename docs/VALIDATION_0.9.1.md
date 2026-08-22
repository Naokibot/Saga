# Saga 0.10.0 validation report

Date: 2026-08-07
Host used for this review: Debian GNU/Linux 13, x86-64, CPython 3.13.5, Go 1.23.2.

## Results

| Validation | Result |
|---|---:|
| Python unit/regression suite | 126 / 126 passed |
| Installed Saga self-conformance | 12 / 12 passed |
| Python/Go PCL1 differential suite | 14 / 14 passed |
| Standard Core suite | 126 / 126 passed |
| Go unit tests | passed |
| `go vet` | passed |
| Go race detector | passed |
| Random parse smoke | 100,000 inputs, 0 unexpected host exceptions |
| Random expression execution | 25,000 inputs, 0 unexpected host exceptions |
| New review regressions | 7 / 7 passed |
| 17 MiB process-output regression | passed |
| Canonical package reproducibility | byte-identical SHA-256 on repeated build |
| Clean virtualenv Wheel install | passed |
| Installed `saga --version` | Saga 0.10.0 |
| Installed self-conformance | 12 / 12 passed |

## Newly exercised boundary cases

1. Global class instance used and mutated inside an isolated `task.spawn` task; task result was `99` while caller state remained `10`.
2. `private` field containing `SECRET` was absent from both `print(instance)` and `text(instance)`.
3. Arabic-Indic numeric literal `١٢٣` was rejected by both implementations instead of being accepted only by Python.
4. WebSocket adapter was verified to set `redirect_limit=0` and `http_no_proxy=['*']`; a simulated 302 redirect was closed and rejected.
5. External process returned 17 MiB stdout successfully, verifying removal of the obsolete 16 MiB language-specific rejection.
6. Canonical `.sagapkg` members were all ZIP `STORED` and repeated builds were byte-identical.

## Not validated on target hardware in this review

- Windows x86-64 execution/installation
- Windows ARM64 execution/installation
- Linux ARM64 execution
- macOS
- Android/iOS hardware
- independent third-party penetration test or conformance laboratory

Cross-compiled binary format checks do not substitute for target-machine execution.
