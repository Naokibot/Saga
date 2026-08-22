# Saga SIR1 Compute Profile 2027 — Preview

Canonical form begins with:

```
SIR1
stage compute
```

Operations are applied in source order to each `f32` logical element:
- `scale k`
- `add k`
- `clamp min max`

Targets: GLSL 4.50/Vulkan GLSL, HLSL 5, MSL 2 and WGSL. The reference workgroup size is 64 in X. `glsl120` is rejected for compute.

`game.shader_ir_compute_reference(source, values)` provides deterministic CPU conformance semantics. Device dispatch, buffer binding and synchronization remain backend responsibilities.
