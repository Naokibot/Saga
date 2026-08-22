from __future__ import annotations
from pathlib import Path


def create_package_sdk(output: str | Path) -> Path:
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Native Saga package template.
    p = out / 'saga-package-template'
    (p / 'tests').mkdir(parents=True, exist_ok=True)
    (p / 'saga.toml').write_text(
        '[project]\nname="hello-package"\nversion="0.1.0"\n'
        'language="0.9"\nentry="lib.saga"\ntest_dir="tests"\n',
        encoding='utf-8',
    )
    (p / 'lib.saga').write_text(
        'fn greet(name: text) -> text = "Hello, " + name\n', encoding='utf-8'
    )
    (p / 'tests' / 'basic.saga').write_text(
        'use "../lib.saga"\nassert(greet("Saga") == "Hello, Saga")\n',
        encoding='utf-8',
    )

    # Existing Python ecosystems can be surfaced only through an explicit
    # function allowlist. The plugin source itself still cannot import modules.
    py = out / 'python-bridge-template'
    py.mkdir(exist_ok=True)
    (py / 'plugin.py').write_text(
        '''# Executed only by Saga's isolated plugin host.
# `numpy` is a read-only facade exposing only names listed in the manifest.
def average(values):
    return numpy.mean(values)

saga_exports = {"average": average}
''',
        encoding='utf-8',
    )
    (py / 'plugin.saga-plugin.json').write_text(
        '{"imports":{"numpy":["mean"]}}\n', encoding='utf-8'
    )
    (py / 'README.md').write_text(
        'The manifest allowlists installed Python-package functions. The plugin '
        'itself cannot import modules; the host exposes only the named surface '
        'inside Saga\'s isolated process/OS sandbox. Third-party packages are '
        'trusted dependencies, not automatically safe code.\n',
        encoding='utf-8',
    )

    # WebAssembly Component Model authoring surface. The current Saga Standard
    # WASM executable target is WASI; Component packages use this WIT bridge.
    wasm = out / 'wasm-component-template'
    wasm.mkdir(exist_ok=True)
    (wasm / 'world.wit').write_text(
        '''package community:example@0.1.0;
interface api { add: func(a: s64, b: s64) -> s64; }
world library { export api; }
''',
        encoding='utf-8',
    )
    (wasm / 'README.md').write_text(
        'Package a WebAssembly Component plus WIT contract in the Saga registry. '
        'The host must explicitly grant each imported capability.\n',
        encoding='utf-8',
    )

    reg = out / 'registry-deployment'
    reg.mkdir(exist_ok=True)
    (reg / 'Dockerfile').write_text(
        '''FROM python:3.13-slim
WORKDIR /app
COPY saga-language.whl /app/
RUN pip install --no-cache-dir /app/saga-language.whl
EXPOSE 7331
CMD ["saga","registry","serve","--root","/data","--host","0.0.0.0","--port","7331"]
''',
        encoding='utf-8',
    )
    (reg / 'README.md').write_text(
        'Deployable reference registry. For public Internet operation place TLS, '
        'rate limiting, abuse handling, publisher account management and durable '
        'backup in front of this service. Packages may carry Ed25519 publisher '
        'signatures and static capability metadata.\n',
        encoding='utf-8',
    )

    (out / 'ECOSYSTEM_POLICY.md').write_text(
        '''# Saga ecosystem policy

- `.sagapkg` is canonical and reproducible.
- Every downloaded package is SHA-256 verified.
- Versions are explicit in `saga.dependencies.json`; `pkg:` imports never float to a new version.
- Ed25519 publisher signatures are supported and verified during install.
- Registry metadata includes the package's statically inferred minimum capability categories.
- Extension packages may be native Saga, allowlisted isolated Python-package bridges, or WebAssembly Components with WIT contracts.
- Python bridge packages remain trusted third-party code even though authority is reduced by process/OS isolation and a value-only boundary.
- A public service must add TLS, abuse controls, publisher identity/account recovery and operational monitoring around the reference registry.
''',
        encoding='utf-8',
    )
    return out
