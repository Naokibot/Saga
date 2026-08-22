# Saga 0.15.0 feature audit

Date: 2026-08-09
Language edition: Saga 1.0 RC1
Primary implementation: Saga Native 0.15.0

## Language and toolchain

Standard Core semantics remain frozen at 1.0 RC1. Existing variables/types/exact numbers/collections/control flow/functions/lexical closures/classes/interfaces/generics/exceptions/option/result/enums/records/exhaustive match/packages/tasks/diagnostics/tooling remain available. This release does not move game-backend behavior into Standard Core.

## Native game surface

The Native `game` module contains 85 statically typed functions. Its machine-readable manifest is `compatibility/native-game-api-0.15.0.json`.

### Portable Game Profile

Implemented natively in the Saga Native runtime:

- canonical RGBA8 framebuffer with deterministic integer source-over blending;
- pixel, filled rectangle, line and circle raster operations;
- PNG/JPEG decode to RGBA8 with pre-decode file/dimension limits;
- texture draw/region scaling;
- texture-sheet sprite animation;
- camera transform;
- integer tilemaps and atlas rendering;
- particle simulation/drawing;
- lightweight AABB 2D physics with gravity, mass, force, impulse and restitution;
- RIFF/WAVE PCM decode (mono/stereo; 8/16-bit -> PCM16);
- concurrent-safe texture/audio asset cache;
- existing 18-function terminal game baseline.

### Desktop Game Profile

Implemented by the optional Saga Native `sagadesktop+cgo` backend:

- resizable native SDL2 window;
- non-blocking keyboard and mouse state;
- standardized SDL game-controller enumeration/buttons/axes;
- queued PCM16 audio playback;
- OpenGL framebuffer upload/presentation;
- renderer diagnostics;
- fragment shader compilation/link;
- explicit vertex+fragment shader-program compilation/link;
- serialized OS-thread dispatch for SDL/OpenGL operations.

SDL2/OpenGL are reference implementation choices, not normative Saga semantics. The profile is specified in `spec/SAGA_GAME_PROFILE_1.0_RC1.md` so another implementation can use Direct3D, Metal, Vulkan or another backend.

## Standards-readiness engineering

Saga Native now implements `saga standards`. Registry schema 2 separates:

- pre-submission evidence;
- NP acceptance evidence;
- engineering-maturity evidence.

The registry stores evidence by SHA-256, hash-chains events, verifies tampering, restricts proposer role categories, records base-document/committee context/ballot evidence, and calculates the 4-or-5 active-P-member participation threshold from recorded committee P-member count. It does not claim standards-body acceptance.

## International-use engineering retained

- UTF-8 source and vendored Unicode 15.1 identifier profile;
- locale-independent core semantics;
- stable diagnostic IDs independent of translated wording;
- English complete fallback catalog, Japanese broad catalog, partial French/Spanish/German catalogs;
- Native and Python Standard Core implementations;
- deterministic packaging and fixed-point Saga-sourced compiler proof;
- explicit optional hosted profiles and machine-readable compatibility manifests.
