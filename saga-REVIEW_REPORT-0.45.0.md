# Saga 0.45.0 review

## Findings addressed

1. **Python/Go semantic drift:** the Go implementation already exposed Edition 2027 async/resource constructs that were not consistently represented in the Python reference language. A portable subset is now implemented in both common paths.
2. **Async public ABI ambiguity:** async functions declared `-> T` were not portable in the common module interface. Public callers now observe and serialize `future[T]` consistently.
3. **Keyword compatibility risk:** making common words hard keywords would break older source using names such as `await` or `move`. The 0.45 parser treats the new words contextually, including delimiter/operator and end-of-line disambiguation.
4. **Trailing-closure ambiguity in `using`:** the initializer parser could consume the resource-scope `{` as a trailing closure. Both parsers now use control-header parsing so the block delimiter remains unambiguous.
5. **Cleanup across early exits:** `defer` is tied to lexical execution frames and runs LIFO on return/error paths; first-class closures use the same rule.
6. **Resource double-use:** `move` marks known resource bindings consumed, and reassignment of mutable bindings explicitly restores ownership.
7. **Unstructured async lifetime:** `taskgroup` joins outstanding Saga async work before the lexical scope is left.
8. **Task-pool implementation parity:** the Python reference had `task.pool`, `task.submit`, and `task.shutdown`, while the Go implementation did not. The Go runtime now provides the same hosted task-pool surface, including deterministic `using` cleanup and move-only treatment.

## Design review

The release does not attempt to copy whole languages. In particular:

- no global borrow checker was introduced;
- no raw-pointer or unchecked C memory semantics were introduced;
- no JavaScript/TypeScript null/undefined model was introduced;
- no unrestricted Ruby-style runtime metaprogramming was introduced;
- no implicit mutable memory sharing was added to async execution.

The result stays aligned with Saga's managed-memory, exact-number, statically checked, capability-aware design.

## Remaining boundaries

- Hosted async scheduling depends on the host executor and is not deterministic real-time scheduling.
- Cancellation is cooperative/best-effort at the host Future boundary; arbitrary native work may not be interruptible.
- `move` is resource-oriented, not a proof system for every alias that a foreign/native extension could create outside Saga's checked value model.
- Finite differential tests do not prove complete Python/Go semantic equivalence.
- Physical drone/motor/PLC and hard-real-time claims remain governed by their existing hardware qualification boundaries.
