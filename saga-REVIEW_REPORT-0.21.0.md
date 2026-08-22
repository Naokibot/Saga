# Saga 0.21.0 Review Report

## Objective

Strengthen use cases that were weak in 0.20 without weakening Saga's beginner-facing syntax, safety defaults, or SH-3 self-hosting boundary.

## Defects found and corrected during review

1. **HTTP accept close race.** `http.accept()` could block if close happened after the initial closed check. A server `Done` signal and select-based accept were added.
2. **HTTP response/close race.** E2E testing found that `respond()` could return after channel enqueue but before the host handler wrote bytes, allowing immediate close to produce an empty client response. Response ACK synchronization now makes `respond()` wait for host write completion or request cancellation.
3. **HTTP status validation too broad.** Accepted status was 100..999; restricted to 100..599.
4. **DB temporary-file cross-handle collision.** Persistence now serializes normalized database paths with a path-level mutex in addition to handle locking.
5. **3D depth interpolation.** Initial screen-space linear z interpolation was replaced with reciprocal-depth interpolation for perspective depth testing.
6. **3D asset usability.** Initial 3D API required hand-authored flat arrays. Added Wavefront OBJ vertex/face loading and polygon fan triangulation.
7. **Browser host capability ambiguity.** DOM/storage functions now report browser availability and fail closed on non-browser profiles instead of pretending the capability exists.
8. **SH-3 browser host boundary.** Generic `host_available`/`host_call` primitives were added to the language-neutral seed, while browser operation semantics remain outside the Saga grammar/type implementation. Full SH-3 qualification was rerun and remained PASS.
9. **Example correctness.** The first HTTP example incorrectly used option-only `unwrap_or` on a result. The example was corrected to `unwrap_err` and all added examples are statically checked.

## Architecture decisions

- The browser target runs the canonical SH-3 Saga kernel rather than introducing a second JavaScript implementation of Saga semantics.
- PWA is the mobile deployment baseline for this release; native mobile claims remain separate.
- HTTP request/response ownership avoids passing the host `ResponseWriter` into Saga code.
- DB transactions are deliberately described as optimistic single-process application transactions, not as a relational distributed database.
- 3D begins with a deterministic CPU framebuffer path so it can be tested without a physical GPU. A future GPU 3D profile can reuse the mesh/camera concepts without making hardware evidence a prerequisite for this baseline.
- `sys` gains non-secret platform facts but no ambient environment-variable read in this expansion.

## Result

The largest weak practical use cases now have real baselines: interactive/offline Web/PWA, an HTTP backend, persistent transactional application state, and software 3D with asset loading. Remaining large gaps are native Android/iOS SDK/toolchain integration, a production web framework ecosystem, a full GPU/AAA 3D stack, multi-process database semantics and complete OS-kernel facilities.
