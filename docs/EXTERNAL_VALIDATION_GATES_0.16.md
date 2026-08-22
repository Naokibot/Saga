# External validation gates for Saga 0.16

The following cannot be self-certified by a Linux development container:

1. Windows real-host Direct3D presentation and input.
2. macOS real-host Metal presentation and input.
3. Physical gamepad button/axis behavior.
4. Hardware GPU driver execution rather than software rasterization.
5. Full Vulkan surface/swapchain/present with a Vulkan ICD.
6. Organizationally independent second implementation.
7. Third-party conformance laboratory certificate.
8. Public Internet package-registry availability and operations.

The release includes executable probes/evidence formats for each relevant gate. A gate becomes PASS only when evidence produced on the required external target is attached and independently reviewable.
