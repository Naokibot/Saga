# Saga Native installers

Saga 0.12 native installers do not create a Python virtual environment and do
not require Python, Go or clang.

Linux x86-64:

```bash
chmod +x saga-installer-linux-amd64-0.13.0.run
./saga-installer-linux-amd64-0.13.0.run
saga --version
saga conformance --json
```

Windows x86-64:

```powershell
.\saga-installer-windows-amd64-0.13.0.exe
saga --version
```

Use `--prefix <dir>` for an isolated/custom installation and `--uninstall` to
remove it.
