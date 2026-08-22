# Saga 0.12.0 General-Purpose and Ecosystem Audit

Saga retains the Standard Core and 27-module / 149-function Hosted API surface validated in 0.10.1 and adds lexical closures, package registry/interoperability, build targets and mobile runtime generation.

## Core additions validated

- nested lexical functions and mutable closure capture in both Python and Go;
- fixed-version network package installation and `pkg:` source imports;
- SHA-256 + optional Ed25519 package publisher validation;
- package capability metadata and `saga capabilities` preview;
- Standard runtime-AOT native and WASI bundles;
- direct-C scalar native/WASM backend;
- Python-free Standard Core mobile runtime source for iOS/Android;
- allowlisted bridge to installed Python libraries while preserving isolated execution;
- WIT/WebAssembly Component author SDK.

## Ecosystem reality

The mechanisms required to grow a third-party ecosystem now exist, and existing Python/WASM ecosystems can be bridged. The project does not claim that a large population of independent Saga-native third-party packages already exists, nor that a public Internet registry is currently operated by the project.
