# Windows/macOS native-host qualification

The purpose is to prove the current Saga source executes on the named operating system. A cross-built PE/Mach-O artifact is insufficient.

## Prerequisites

- the unchanged Saga 0.26.2 review source and `release/source-manifest-0.26.2.json`
- Python 3.13-compatible runtime and Go 1.23-compatible toolchain
- no pre-generated `validation/native-host-*.json` copied from another host

## Commands

On Windows:

```powershell
python tools/review_evidence.py --verify release/source-manifest-0.26.2.json
python tools/native_host_qualification.py --expected-host windows
```

On macOS:

```sh
python tools/review_evidence.py --verify release/source-manifest-0.26.2.json
python tools/native_host_qualification.py --expected-host macos
```

Linux can be repeated with `--expected-host linux` for comparison.

The evidence records OS/architecture, source-manifest identity, Go build/test/vet, the Native binary hash, conformance, type-checking and a real Saga execution result. The tool refuses a mismatched expected host.

The GitHub workflow is a reproducible *native-OS hosted-runner* path. Do not relabel hosted VM evidence as physical-machine evidence; a reviewer may additionally repeat it on controlled physical hosts.
