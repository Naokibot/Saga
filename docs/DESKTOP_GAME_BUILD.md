# Building the Saga Native Desktop Game reference backend

The ordinary Saga Native binary does not require SDL2/OpenGL. Desktop Game is an optional build profile.

## Linux reference build

Install an SDL2 development package and an OpenGL-capable driver, then build the Native implementation with:

```bash
cd implementations/go
go build -tags sagadesktop -o saga-native-desktop ./cmd/saga-go
```

The validation environment used SDL2's X11 backend under Xvfb. A normal desktop may use X11 or Wayland according to the installed SDL2 build.

## Windows source build

The backend source has Windows cgo link directives for SDL2. A source build requires a cgo-capable C toolchain plus SDL2 import libraries discoverable by the linker. This release cross-builds and format-checks the dependency-free Windows Saga Native binaries, but does **not** claim a validated Windows `sagadesktop` build because this Linux validation host does not provide a Windows SDL2/cgo toolchain or Windows device execution.

## macOS source build

The backend source has Darwin cgo link directives for SDL2 and uses an SDL-created OpenGL context. A source build requires SDL2 development libraries and a cgo-capable local toolchain. This release does **not** claim a validated macOS Desktop Game binary or physical Mac test.

## Runtime disclosure

A desktop-enabled binary reports:

```json
"native_host_dependencies": ["SDL2", "OpenGL-capable graphics driver"]
```

`runtime_dependencies` remains reserved for programming-language runtime/toolchain dependencies; Saga does not require Python, Java, Node.js or .NET to execute the built desktop binary.

## Backend portability

`spec/SAGA_GAME_PROFILE_1.0_RC1.md` is normative at the Saga API level. SDL2/OpenGL is only the current reference backend. Other implementations are free to use Direct3D, Metal, Vulkan or a software renderer.
