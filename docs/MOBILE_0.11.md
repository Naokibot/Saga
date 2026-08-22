# Saga 0.11 mobile runtimes

`saga mobile ios` and `saga mobile android` always generate `StandardCoreRuntime`, a Python-free Go package containing the independent Standard Core implementation and the linked Saga program. The build scripts use `gomobile bind` to produce an XCFramework or Android AAR on supported vendor toolchains.

When the source fits the Saga scalar AOT profile, an additional tiny direct-C runtime is generated. This gives small applications a lower-overhead path without reducing the semantics available to normal Standard Core programs.

Generation is not equivalent to vendor certification. iOS device distribution requires macOS/Xcode, valid signing and provisioning. Android AAR/APK/device validation requires Android SDK/NDK/Gradle and target hardware/emulators.
