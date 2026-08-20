# Saga 0.50.0 review — Production GA Control

## Review scope

The review covered the Python reference compiler/runtime, the independent Go checker/runtime, the native codegen path, machine-control primitives, project production gate and release/evidence tooling.

## Findings fixed

### High — control helper escape from `@control_tick`

0.49 validated the syntax inside a `@control_tick` body but a tick could call an ordinary helper whose body performed allocation, blocking I/O or another forbidden operation. 0.50 adds `@control_safe` and whole-call-graph checking in both implementations. Unverified helpers, recursion and indirect calls fail at compile time.

### High — production control could mutate shared state directly

A bounded tick could write a global or arbitrary object field. 0.50 rejects shared/global variable assignment and direct arbitrary member mutation in the Production GA control surface. Audited deterministic `machine.*` state primitives remain the explicit stateful path.

### Medium — raw or time-dependent calls were not fail-closed by default

0.49 used a forbidden-call list, which can miss a newly added API. 0.50 uses a strict allowlist for Production GA control calls. Unknown machine calls and external modules are rejected rather than silently admitted.

### Medium — literal range was bounded in shape but not in size

A literal range could still contain an impractically large number of iterations. 0.50 rejects Production GA control loops above 4096 statically known iterations; target-specific WCET evidence is still required for deployment.

### Medium — machine production project gate lacked a safety-case binding

0.49 validated compile/lint/lock/reproducibility but did not bind hazard/WCET/HIL evidence to the exact project source. 0.50 adds `production-check --machine` and a confined, source-hash-bound `machine-safety.toml` evidence contract.

### Medium — rejected HTTP redirects could defer socket cleanup

The capability-aware redirect handler correctly rejected unauthorized redirect targets, but the rejected response object was not explicitly closed on that exception path. In a long-running control host, repeated rejected redirects could accumulate socket resources until garbage collection. 0.50 closes the response immediately on authorization failure and closes `HTTPError` response objects after bounded copying. The regression suite reruns the affected HTTP tests with `ResourceWarning` promoted to an error.

### Medium — contextual `move` parser regression

`move` is designed to remain usable as an ordinary identifier outside prefix-operator position. Both parsers incorrectly treated `move < 0` (and related operator-followed spellings) as a prefix move expression. The contextual-prefix delimiter/operator set now includes comparison, equality, logical and range operators. The bundled Othello self-play regression passes again.

## Safety boundary retained

The language/toolchain does not claim that hosted Python/Go execution is hard real-time, does not make hidden motion/safety decisions, and does not replace independent E-stop/STO/interlock hardware. A machine deployment is not certified merely because Saga 0.50 itself is Production GA.

## Release decision rule

The release is considered Production GA only when `validation/production-ga-0.50.0.json` is source-manifest bound and has `pass: true`. Qualification uses resumable, source-bound checkpoints; a source-manifest or source-tree hash change invalidates prior checkpoint results instead of reusing stale PASS evidence. The qualification intentionally fails closed on any failed regression, security audit, Go test/vet/race check, control invariant test, native reproducibility test or machine-gate source-binding test.
