# Saga 0.12.0 validation report

## Environment

Validated on Linux x86-64 in the release environment. Linux ARM64 and Windows
x86-64/ARM64 binaries were cross-built and format inspected but were not run on
those target machines in this environment.

## Results

| Validation | Result |
|---|---:|
| Python reference regression suite | 150 / 150 PASS |
| Saga Native Go unit tests | PASS |
| `go vet` native implementation | PASS |
| Go Race Detector | PASS |
| Native installer Go tests | PASS |
| Saga Native Standard Core self-conformance | 11 / 11 PASS |
| Linux x86-64 Saga Native format | static ELF x86-64 |
| `ldd` on Saga Native | `not a dynamic executable` |
| Empty-PATH native install | PASS |
| Empty-PATH `saga --version` | PASS |
| Empty-PATH `saga info` | PASS, `runtime_dependencies=[]` |
| Empty-PATH self-conformance | PASS |
| Empty-PATH standalone build | PASS |
| Empty-PATH standalone execution | PASS (`41`, `42`) |
| Empty-PATH uninstall | PASS |
| Linux ARM64 native runtime | ELF AArch64 format verified |
| Windows x86-64 native runtime | PE32+ x86-64 format verified |
| Windows ARM64 native runtime | PE32+ ARM64 format verified |

## Dependency proof

The Linux x86-64 Saga Native executable is produced with `CGO_ENABLED=0` and is
statically linked. The native installer was executed with `PATH=/nonexistent`;
therefore Python, Go, clang, Java, Node and similar tools were not discoverable
or callable during installation, conformance, build or application execution.

## Standalone application test

The tested program used a mutable lexical closure. `saga build` produced a
standalone ELF application. With an empty PATH the application printed:

```text
41
42
```

The application payload is canonical JSON protected by SHA-256 and verified
before execution.

## Not claimed

- Windows or ARM64 execution on real target hardware;
- source-self-hosted compiler implementation;
- ISO/IEC publication or approval;
- independence of optional third-party hosted libraries from their own vendor
  dependencies.
