# Saga Graphics Backend ABI — 1.0 RC1

Status: project interoperability profile for Saga Language Edition 1.0 RC1. It is not an ISO/IEC standard.

## 1. Purpose
This profile separates Saga-level observable graphics behavior from a particular graphics API. Backends may use OpenGL, Vulkan, Direct3D, Metal, WebGPU or software rendering.

## 2. Canonical presentation input
The portable presentation image is tightly packed row-major RGBA8, top-left origin, +x right, +y down, straight alpha. A backend that natively consumes BGRA shall perform a semantics-preserving channel conversion.

## 3. Backend lifecycle
A backend shall expose create, capability query, present and idempotent destruction. Creation failures and device/surface loss shall become explicit Saga errors. A backend must not silently report hardware acceleration when it is using software rasterization.

## 4. Window/surface coupling
If a backend requires a backend-specific native window flag or surface, it may recreate the implementation-owned native window before renderer creation, provided Saga-level dimensions/title/input semantics are preserved. Swapchain resize/out-of-date conditions shall be explicit and shall not permit out-of-bounds framebuffer transfer.

## 5. Synchronization
Presentation shall obey the backend's queue/thread-affinity rules. The implementation shall prevent ordinary Saga tasks from racing unsafe window, device, queue or context state.

## 6. Portable shader boundary
SIR1 is the normative portable shader interchange for the RC1 game profile. Backend source languages and binary formats are implementation details. Canonical SIR1 and its SHA-256 digest provide a backend-neutral identity. A backend may expose native shaders in addition to SIR1 but shall not redefine SIR1 semantics.

## 7. Evidence
Backend conformance evidence shall record OS/architecture, backend/API version, device/adapter, software-versus-hardware status, framebuffer format, every skipped capability, and whether presentation actually reached the target API's present operation. Compilation or loader discovery alone is not presentation validation.
