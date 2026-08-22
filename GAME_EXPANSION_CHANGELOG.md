# Saga Native game capability expansion — 2026-08-09

This package is based on Saga 0.14.0 / Language Edition 1.0 RC1 and expands the dependency-free Native game API from 13 to 18 functions.

Added:
- `game.fill_rect`
- `game.line`
- `game.circle`
- `game.sprite`
- `game.point_in_rect`
- `examples/game/shape_arena.saga`

Fixed:
- `docs/GAME_DEVELOPMENT.md` used an invalid three-argument `game.canvas` call even though the implementation and type checker define two arguments.

Validation performed in the Linux x86-64 execution environment:
- full Go unit/regression suite PASS
- go vet PASS
- full Go Race Detector suite PASS
- game-focused tests PASS
- `shape_arena.saga` check + run PASS
- `mini_dodge.saga` run PASS

This expansion materially improves actual game authoring for terminal 2D games. It does not claim a GPU/window/audio backend.
