# Saga 0.37.0 Reviewer Handoff

## Release identity

- Release: **Saga 0.37.0**
- Theme: Low-Pause Runtime + Open-World Dispatch + Scale/Endurance Qualification
- Native Runtime ABI: **0.35** (additive APIs; existing native value/layout ABI retained)

## Fast reproduction path

From the extracted source root:

```bash
python tools/review_evidence.py --verify release/source-manifest-0.37.0.json
python tools/runtime_037_qualification.py
python tools/cross_implementation_validation.py
python tools/module_conformance.py
python tools/native_runtime_qualification_035.py
python tools/native_codegen_qualification.py
python tools/machine_control_qualification.py
python tools/internal_security_audit.py
python tools/spec_review_lint.py
python tools/validate_native_game_api.py
(cd implementations/go && go test ./... && go vet ./...)
```

Optional scale/simulation evidence:

```bash
python tools/ecosystem_scale_qualification.py
python tools/desktop_cross_platform_qualification_037.py
python tools/industrial_endurance_simulation_037.py
```

The final command simulates seven days by default and does **not** touch physical industrial equipment.

## Review focus

### Runtime
- verify major mark and sweep budgets under low-pause mode;
- verify minor collection is still documented as STW;
- inspect allocations made during incremental sweep;
- run sanitizer builds where available.

### Open-world dispatch
- build a base module, then register an external subtype/method without rebuilding that base;
- stress concurrent idempotent registration;
- verify type/interface ancestry and slot lookup fail closed;
- verify public ABI header type/slot constants;
- verify mixed pre-0.37 binaries are not assumed to participate in registry dispatch without rebuild/registration.

### Generics
- import a generic function/class from another module;
- exercise inferred and explicit concrete instantiations;
- inspect caller-local specialized symbols and incremental-build invalidation.

### Tooling
- confirm nested lexical watches;
- inspect bounded debug recordings and truncation counters;
- inspect statement profile semantics and heap data;
- note that profiling is interval-based, not CPU-instruction attribution.

### Ecosystem
- confirm SQLite connection closure and WAL behavior;
- test FTS5 trigram and SQL fallback;
- do not interpret synthetic 100k package-version data as real adoption.

### Desktop / industrial evidence boundary
- Windows/macOS physical execution is UNEXECUTED on the supplied review host;
- industrial seven-day evidence is an accelerated deterministic digital twin;
- require separate physical HIL/rig evidence before any production industrial claim.
