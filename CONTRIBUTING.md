# Contributing to Saga

Saga is a programming-language and toolchain project. Changes should preserve readability, deterministic behavior where promised, and the explicit distinction between software qualification and physical-machine certification.

## Development setup

Requirements:

- Python 3.13+
- Go toolchain compatible with `implementations/go`
- Git

Create an isolated Python environment, then install the project and development test dependency in editable mode:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

On Windows PowerShell, activate with:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Before opening a pull request

Run at least:

```bash
python -m compileall -q saga tools
python -m unittest tests.test_control_ga_050 tests.test_production_industrial_049 tests.test_virtual_hil_048 tests.test_advanced_motion_047 tests.test_precision_machine_046 tests.test_language_synthesis_045
python -m pytest -q tests/test_machine_control_028.py tests/test_machine_control_036.py tests/test_precision_machine_046.py tests/test_advanced_motion_047.py tests/test_production_industrial_049.py
cd implementations/go
go test ./...
go vet ./...
```

Changes to native-host, platform, registry, mobile, or physical-lab behavior should also run the matching qualification workflow or tool when the required host/hardware/credentials are available.

## Pull-request rules

- Keep one coherent purpose per PR.
- Explain user-visible language or ABI changes.
- Add or update tests for behavior changes.
- Do not claim physical HIL, WCET, SIL/PL, fieldbus, motor/drive, device, or security certification without the corresponding evidence.
- Do not commit credentials, signing keys, tokens, generated virtual environments, caches, or local CI evidence.
- Preserve historical release evidence; new development should not rewrite an old frozen manifest to make it match a changed tree.

## Release evidence

`release/source-manifest-*.json` files describe frozen historical source candidates. Once a release is frozen, later maintenance work on `main` is expected to diverge from that historical manifest. Release qualification must bind a new release candidate to a new manifest rather than modifying old evidence.
