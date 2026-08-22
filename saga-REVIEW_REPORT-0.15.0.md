# Saga 0.15.0 source review report

## Review objective

Extend Saga from a terminal-game-capable language into a genuinely usable native 2D game-development baseline while preserving the language's independence, portability and standards-oriented semantics.

## Defects/issues found and corrected

1. **Desktop resources used close-request state as destruction state.** Window close requests are now separated from actual resource destruction. Renderer teardown is ordered before window destruction.
2. **SDL/OpenGL thread-affinity risk.** Desktop backend calls are serialized through a dedicated goroutine locked to one OS thread.
3. **Shader coverage was fragment-only.** Added explicit vertex+fragment shader-program compilation/link while retaining a simple fragment API.
4. **Game asset decode accepted format by decoder fallback.** Texture loading is now explicitly PNG/JPEG and performs header/dimension checks before full decode.
5. **Unbounded asset file reads.** Saga Native now has documented implementation-level texture/WAV byte and texture dimension/pixel limits, exposed by `saga info`.
6. **Standardization documentation/Native CLI mismatch.** Documentation referenced `saga standards` while the primary Native CLI did not implement it. A Native evidence registry is now implemented and tested.
7. **Standardization readiness conflated process stages.** Registry schema 2 separates pre-submission evidence, NP ballot acceptance evidence, and engineering maturity; 4/5 P-member thresholds are committee-size aware.
8. **Desktop dependencies could be misunderstood as default runtime dependencies.** `saga info` now reports optional native host dependencies separately while retaining `runtime_dependencies: []` for programming-language runtimes.

## Architecture decisions

- Standard Core remains backend-neutral and does not depend on SDL/OpenGL.
- Portable Game is an optional, backend-neutral Saga profile and runs in the normal native runtime.
- Desktop Game is an optional hosted profile. SDL2/OpenGL is the reference backend, not the specification.
- GPU shader source remains backend-language-specific in RC1. A future portable shader IR is deliberately not invented without multi-backend experience.
- 2D physics is explicitly a lightweight deterministic-step AABB baseline rather than being mislabeled as a full rigid-body engine.

## Result

Saga 0.15.0 can build nontrivial terminal and framebuffer-based 2D game logic with Native Saga alone, and the desktop profile can open a native window, query real-time input state, present RGBA frames through OpenGL, compile/link shaders, and queue WAV audio through SDL2 on the validated Linux environment.
