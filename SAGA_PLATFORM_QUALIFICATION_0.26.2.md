# Saga 0.26.2 platform and external-evidence qualification

`tools/platform_qualification.py` inventories implementation availability and live evidence without conflating the two. Missing hardware, credentials or independent attestations are BLOCKED/READY_UNEXECUTED rather than PASS.

Core GA evidence is evaluated by `tools/ga_readiness.py`, which re-binds accepted evidence to the exact current source manifest/tree and gate-specific mandatory checks. A JSON field saying `pass: true` is not sufficient by itself.

For reviewer-facing native Windows/macOS evidence use `tools/native_host_qualification.py`; the expected host must match the actual OS and target-host build/start/conformance/check/run evidence is recorded with the binary SHA-256 and source binding. Cross-build format checks remain separate.

For public Registry evidence use `tools/registry_live_qualification.py`. The public gate requires verified HTTPS, a globally routable **actual connected TLS peer**, current-source binding, explicit publisher trust, immutable-version rejection and Python↔Go signed publish/search/install. Every qualification run uses a unique package identity so the test can be repeated without weakening immutability.

For independent audit evidence use `tools/verify_external_security_attestation.py`. Exact current source-manifest identity, exact report SHA-256, reviewer identity/scope/methods and zero open Critical/High findings are mandatory.

Optional live profiles such as physical Vulkan/gamepad/GPIO, AWS, Spark, pygame and mobile devices remain separate platform evidence. They do not substitute for the four mandatory external Core GA tracks.
