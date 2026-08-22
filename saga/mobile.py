from __future__ import annotations
from pathlib import Path
import json

from .aot import emit_c, _embedded_standard_go, AOTError
from .api import compile_file


def _mobile_c(source: str | Path) -> str:
    return emit_c(Path(source).resolve(), wasm=False).replace(
        'int main(void) {', 'int saga_mobile_main(void) {'
    )


def _try_mobile_c(source: str | Path) -> str | None:
    try:
        return _mobile_c(source)
    except AOTError:
        return None


def _write_standard_core_mobile_runtime(source: str | Path, destination: Path) -> Path:
    """Create a Python-free Standard Core Go package for gomobile bind."""
    source = Path(source).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    go_root = Path(__file__).resolve().parents[1] / 'implementations' / 'go' / 'cmd' / 'saga-go'
    core_files = [
        'annotations.go', 'ast.go', 'builtins.go', 'checker.go', 'control_profile_047.go', 'lexer.go', 'optimizer.go', 'parser.go',
        'runtime.go', 'runtime_values.go', 'token.go', 'types.go', 'unicode15_1.go',
    ]
    for name in core_files:
        text = (go_root / name).read_text(encoding='utf-8').replace(
            'package main', 'package sagaruntime', 1
        )
        (destination / name).write_text(text, encoding='utf-8')
    loaded = compile_file(str(source))
    (destination / 'embedded_source.go').write_text(
        _embedded_standard_go(loaded, package_name='sagaruntime'),
        encoding='utf-8',
    )
    (destination / 'mobile_support.go').write_text(
        '''package sagaruntime

import "fmt"

const sagaGoVersion = "0.50.0"
var sagaProcessArgs = []string{}
var sagaToolchainMode = false

// Compiler/build operations are deliberately unavailable inside an embedded
// mobile application runtime. The language core still type-checks and runs
// embedded Saga source without invoking host toolchain processes.
func loadProgram(path string) ([]Stmt, error) {
    return nil, fmt.Errorf("compiler module unavailable in mobile runtime: %s", path)
}
func buildStandalone(input, output string) (string, error) {
    return "", fmt.Errorf("compiler.build unavailable in mobile runtime")
}
func buildStandaloneKind(input, output, kind string) (string, error) {
    return "", fmt.Errorf("compiler.build unavailable in mobile runtime")
}
func numberToInt(v Value) (int, error) {
    n, ok := v.(Number)
    if !ok { return 0, fmt.Errorf("int required") }
    x, ok := n.Int()
    if !ok || !x.IsInt64() { return 0, fmt.Errorf("host-sized int required") }
    return int(x.Int64()), nil
}

// Hosted/unsafe resources are intentionally represented only enough for the
// shared Standard Core interpreter to compile. No mobile adapter silently
// acquires filesystem/network/FFI/JIT/desktop capabilities.
type mobileCloser interface { Close() error }
type FFIPointer struct { Addr uintptr; Owner bool; Freed bool }
type FFICallback struct{}
type KVDBValue struct { Closed bool }
type TCPConnValue struct { Conn mobileCloser }
type TCPListenerValue struct { Listener mobileCloser }
type GameCanvas struct { W int; H int }
type GameRenderer struct { Handle uintptr }
type GameWindow struct { Renderer *GameRenderer; Handle uintptr; Closed bool; ShouldClose bool }
type GameShader struct { Handle uintptr; Renderer *GameRenderer }
type GamepadHandle struct { Handle uintptr }
type JITFunctionValue struct { Handle uintptr; closed bool }

// Mobile embeds already-selected source and therefore never reads .smi.json
// files at runtime. Keep the public interface shape required by the shared
// checker so module-aware AST/checker code compiles without granting file IO.
type ModuleInterface struct {
    Schema string
    LanguageVersion string
    Module string
    SourceSHA256 string
    Exports []map[string]interface{}
    Dependencies []map[string]string
    ABISHA256 string
    BuildSHA256 string
}

func ffiFreePointer(p *FFIPointer) error { p.Freed = true; p.Addr = 0; return nil }
func ffiCloseCallbackValue(*FFICallback) {}
func destroyGameRenderer(*GameRenderer) {}
func desktopCloseWindow(uintptr) {}
func desktopShaderDestroy(uintptr, uintptr) {}
func desktopCloseGamepad(uintptr) {}
func jitRelease(uintptr) {}

func (i *Interpreter) callNativeModule(module, name string, args []Value, t Token) (Value, error) {
    return nil, i.rerr(t, "SAGA-R103", "host module unavailable in Standard Core mobile runtime: "+module+"."+name)
}
func (i *Interpreter) callFFI(name string, args []Value, t Token) (Value, error) {
    return nil, i.rerr(t, "SAGA-R188", "FFI unavailable in Standard Core mobile runtime")
}
func (i *Interpreter) callJIT(name string, args []Value, t Token) (Value, error) {
    return nil, i.rerr(t, "SAGA-R188", "JIT unavailable in Standard Core mobile runtime")
}
func (i *Interpreter) callExtern(d *FnDecl, args []Value, t Token) (Value, error) {
    return nil, i.rerr(t, "SAGA-R188", "extern unavailable in Standard Core mobile runtime")
}
''',
        encoding='utf-8',
    )
    (destination / 'mobile.go').write_text(
        '''package sagaruntime

import "strings"

// Run executes the embedded Saga Standard Core program. The package contains
// the independent Go Standard Core implementation and has no Python runtime
// dependency.
func Run() (string, error) {
    stmts, err := loadEmbeddedProgram()
    if err != nil { return "", err }
    c := NewChecker()
    if err = c.Check(stmts); err != nil { return "", err }
    lines := []string{}
    it := NewInterpreter(c, func(s string) { lines = append(lines, s) })
    if err = it.Interpret(stmts); err != nil { return "", err }
    return strings.Join(lines, "\\n"), nil
}

// RunText is a gomobile-friendly wrapper with a single string result.
func RunText() string {
    out, err := Run()
    if err != nil { return "ERROR: " + err.Error() }
    return out
}
''',
        encoding='utf-8',
    )
    (destination / 'go.mod').write_text(
        'module saga.mobile/runtime\n\ngo 1.23\n', encoding='utf-8'
    )
    return destination


def generate_ios(
    source: str | Path,
    output: str | Path,
    bundle_id: str = 'dev.saga.app',
) -> Path:
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Full Standard Core path: this is the primary mobile runtime.
    _write_standard_core_mobile_runtime(source, out / 'StandardCoreRuntime')
    script = out / 'build-standard-runtime.sh'
    script.write_text(
        '''#!/bin/sh
set -eu
cd "$(dirname "$0")/StandardCoreRuntime"
command -v gomobile >/dev/null || {
  echo "install golang.org/x/mobile/cmd/gomobile first" >&2
  exit 2
}
gomobile bind -target=ios -o ../SagaStandardCore.xcframework .
''',
        encoding='utf-8',
    )
    script.chmod(0o755)

    # Optional tiny direct-C path for programs inside the scalar profile.
    lightweight = _try_mobile_c(source)
    if lightweight is not None:
        runtime = out / 'Sources' / 'SagaRuntime'
        include = runtime / 'include'
        example = out / 'ExampleApp'
        include.mkdir(parents=True, exist_ok=True)
        example.mkdir(parents=True, exist_ok=True)
        (runtime / 'saga_program.c').write_text(lightweight, encoding='utf-8')
        (include / 'SagaRuntime.h').write_text(
            '#pragma once\nint saga_mobile_main(void);\n', encoding='utf-8'
        )
        (out / 'Package.swift').write_text(
            '// swift-tools-version: 6.0\n'
            'import PackageDescription\n'
            'let package = Package('\
            'name: "SagaRuntime", platforms: [.iOS(.v15)], '\
            'products: [.library(name:"SagaRuntime", targets:["SagaRuntime"])], '\
            'targets: [.target(name:"SagaRuntime", publicHeadersPath:"include")])\n',
            encoding='utf-8',
        )
        (example / 'SagaExampleApp.swift').write_text(
            'import SwiftUI\nimport SagaRuntime\n\n'
            '@main struct SagaExampleApp: App { '\
            'var body: some Scene { WindowGroup { ContentView() } } }\n',
            encoding='utf-8',
        )
        (example / 'ContentView.swift').write_text(
            'import SwiftUI\nimport SagaRuntime\n'
            'struct ContentView: View { @State var result: Int32 = 0; '\
            'var body: some View { VStack { Text("Saga result: \\(result)"); '\
            'Button("Run Saga") { result = saga_mobile_main() } } } }\n',
            encoding='utf-8',
        )
    else:
        (out / 'LIGHTWEIGHT_RUNTIME_UNAVAILABLE.md').write_text(
            'This program uses Standard Core features outside the direct-C scalar '
            'profile. Use `StandardCoreRuntime` and build `SagaStandardCore.xcframework`.\n',
            encoding='utf-8',
        )

    (out / 'IOS_BUILD.md').write_text(
        '# Saga iOS native runtime\n\n'
        f'Bundle identifier suggestion: `{bundle_id}`.\n\n'
        '`StandardCoreRuntime` is the primary Python-free runtime and preserves '
        'lexical closures, exact numbers, OOP, generics and exceptions. Run '
        '`build-standard-runtime.sh` on macOS after installing `gomobile` to '
        'produce an XCFramework. If the program fits the scalar profile, a '
        'smaller Swift Package/C runtime is generated as an optional fast path.\n\n'
        'App Store/device distribution requires macOS, Xcode, Apple code '
        'signing and provisioning; generation on another host is not device validation.\n',
        encoding='utf-8',
    )
    return out


def generate_android(
    source: str | Path,
    output: str | Path,
    application_id: str = 'dev.saga.app',
) -> Path:
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Full Standard Core runtime source.
    _write_standard_core_mobile_runtime(source, out / 'StandardCoreRuntime')
    script = out / 'build-standard-runtime.sh'
    script.write_text(
        '''#!/bin/sh
set -eu
mkdir -p "$(dirname "$0")/app/libs"
cd "$(dirname "$0")/StandardCoreRuntime"
command -v gomobile >/dev/null || {
  echo "install golang.org/x/mobile/cmd/gomobile first" >&2
  exit 2
}
gomobile bind -target=android -androidapi 24 -o ../app/libs/sagaruntime.aar .
''',
        encoding='utf-8',
    )
    script.chmod(0o755)

    java = out / 'app' / 'src' / 'main' / 'java' / Path(*application_id.split('.'))
    java.mkdir(parents=True, exist_ok=True)
    lightweight = _try_mobile_c(source)
    if lightweight is not None:
        cpp = out / 'app' / 'src' / 'main' / 'cpp'
        cpp.mkdir(parents=True, exist_ok=True)
        (cpp / 'saga_program.c').write_text(lightweight, encoding='utf-8')
        jni_symbol = 'Java_' + application_id.replace('.', '_') + '_MainActivity_runSaga'
        (cpp / 'saga_jni.c').write_text(
            '#include <jni.h>\nint saga_mobile_main(void);\n'
            f'JNIEXPORT jint JNICALL {jni_symbol}(JNIEnv* env, jobject self) '
            '{ (void)env; (void)self; return (jint)saga_mobile_main(); }\n',
            encoding='utf-8',
        )
        (cpp / 'CMakeLists.txt').write_text(
            'cmake_minimum_required(VERSION 3.22.1)\nproject(saga_runtime C)\n'
            'add_library(saga_runtime SHARED saga_program.c saga_jni.c)\n',
            encoding='utf-8',
        )
        host = (
            f'package {application_id};\n'
            'import android.app.Activity;\nimport android.os.Bundle;\n'
            'import android.widget.TextView;\n'
            'public class MainActivity extends Activity {\n'
            ' static { System.loadLibrary("saga_runtime"); }\n'
            ' public native int runSaga();\n'
            ' @Override public void onCreate(Bundle b) { super.onCreate(b); '
            'TextView v=new TextView(this); v.setText("Saga exit code: "+runSaga()); '
            'setContentView(v); }\n}\n'
        )
        default_config_extra = (
            '  externalNativeBuild { cmake { cppFlags("") } }\n'
            '  ndk { abiFilters += listOf("arm64-v8a", "x86_64") }\n'
        )
        android_extra = ' externalNativeBuild { cmake { path = file("src/main/cpp/CMakeLists.txt") } }\n'
        dependencies = ''
    else:
        host = (
            f'package {application_id};\n'
            'import android.app.Activity;\nimport android.os.Bundle;\n'
            'import android.widget.TextView;\nimport sagaruntime.Sagaruntime;\n'
            'public class MainActivity extends Activity {\n'
            ' @Override public void onCreate(Bundle b) { super.onCreate(b); '
            'TextView v=new TextView(this); v.setText(Sagaruntime.runText()); '
            'setContentView(v); }\n}\n'
        )
        default_config_extra = ''
        android_extra = ''
        dependencies = 'dependencies { implementation(files("libs/sagaruntime.aar")) }\n'
    (java / 'MainActivity.java').write_text(host, encoding='utf-8')

    manifest = out / 'app' / 'src' / 'main' / 'AndroidManifest.xml'
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        '<manifest xmlns:android="http://schemas.android.com/apk/res/android">'
        '<application android:theme="@android:style/Theme.Material.Light" android:label="Saga">'
        '<activity android:name=".MainActivity" android:exported="true">'
        '<intent-filter><action android:name="android.intent.action.MAIN"/>'
        '<category android:name="android.intent.category.LAUNCHER"/></intent-filter>'
        '</activity></application></manifest>\n',
        encoding='utf-8',
    )
    (out / 'settings.gradle.kts').write_text(
        'import org.gradle.api.initialization.resolve.RepositoriesMode\n'
        'pluginManagement { repositories { google(); mavenCentral(); gradlePluginPortal() } }\n'
        'dependencyResolutionManagement { '
        'repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS); '
        'repositories { google(); mavenCentral() } }\n'
        'rootProject.name="SagaAndroidApp"\ninclude(":app")\n',
        encoding='utf-8',
    )
    (out / 'build.gradle.kts').write_text(
        'plugins { id("com.android.application") version "9.3.0" apply false }\n',
        encoding='utf-8',
    )
    (out / 'app' / 'build.gradle.kts').write_text(
        f'plugins {{ id("com.android.application") }}\n'
        f'android {{\n'
        f' namespace = "{application_id}"\n'
        ' compileSdk = 37\n'
        ' defaultConfig {\n'
        f'  applicationId = "{application_id}"\n'
        '  minSdk = 24\n'
        '  targetSdk = 36\n'
        '  ndkVersion = "28.2.13676358"\n'
        + default_config_extra +
        ' }\n'
        + android_extra +
        '}\n'
        + dependencies,
        encoding='utf-8',
    )
    (out / 'ANDROID_BUILD.md').write_text(
        '# Saga native Android runtime\n\n'
        '`StandardCoreRuntime` is the primary Python-free runtime suitable for '
        '`gomobile bind`; it preserves lexical closures, exact numbers, OOP, '
        'generics and exceptions. The Gradle project targets Android API 36 with compile SDK 37 and supports the Standard Core AAR; the lightweight JNI profile targets arm64-v8a/x86_64. '
        'If the source fits the scalar profile, a smaller direct-C/JNI runtime '
        'is generated and used automatically. Otherwise build the AAR using '
        '`build-standard-runtime.sh`. APK/device validation requires Android '
        'SDK/NDK and target devices.\n',
        encoding='utf-8',
    )
    return out
