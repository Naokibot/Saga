# Saga Shader IR (SIR1) — 1.0 RC1

## Purpose
SIR1 is a small deterministic, backend-neutral fragment-color IR. It keeps Saga game source independent of GLSL, HLSL, Metal Shading Language, and WGSL while preserving one observable color-transform model.

## Grammar
A program begins with `SIR1`, then `stage fragment`, then exactly one `sample`, followed by zero or more transforms:

- `invert`
- `grayscale`
- `mul r g b a`
- `bias r g b a`
- `alpha a`

Whitespace is insignificant between tokens. Unknown instructions, duplicate `sample`, transforms before `sample`, non-finite constants, programs over 64 operations, and unsupported stages are errors.

## Semantics
The sampled input is a straight-alpha RGBA vector in normalized 0..1 component space. Operations execute in source order. Output components are clamped to 0..1 at the final write. SIR1 does not permit memory access, loops, recursion, atomics, host calls, undefined derivatives, or implementation-defined resource indexing.

## Required deterministic targets
Saga Native 0.17 defines deterministic source generation for `glsl120`, `glsl450`, `hlsl5`, `msl2`, and `wgsl`. Generated source is an interoperability artifact; a target graphics driver/compiler remains responsible for translating that source to device machine code or its native shader binary form.

## Portability rule
A conforming backend must preserve SIR1 observable RGBA results within the profile's floating-point tolerance. Backend language spellings are non-normative.

## Canonical form and digest

A conforming SIR1 canonicalizer shall emit the semantic program in normalized instruction order using LF line endings, one instruction per line, and finite numeric operands in fixed six-decimal notation. Insignificant source whitespace, CRLF/LF differences, and equivalent decimal spellings shall not change the canonical form.

Saga Native exposes the canonical form through target `sir1` (alias `canonical`) and exposes its lowercase hexadecimal SHA-256 through target `sir1-sha256` (alias `digest`). The digest is over UTF-8 bytes of the canonical form. This digest is intended for package identity, cache keys, differential conformance, and evidence exchange; it is not a digital signature.

## Backend boundary

SIR1 defines portable shader meaning, not a vendor graphics API. `glsl450`/`vulkan-glsl`, `hlsl5`/`direct3d`, `msl2`/`metal`, and `wgsl` are deterministic source-generation targets. A Vulkan implementation still requires a SPIR-V creation path before SIR1 can become a programmable Vulkan shader module. A framebuffer-transfer-only Vulkan presentation backend may conform to Desktop presentation without claiming programmable Vulkan-shader support.
