$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Get-Command py -ErrorAction SilentlyContinue
if ($Python) {
    & py -3 "$ScriptDir\install_saga.py" @args
} else {
    & python "$ScriptDir\install_saga.py" @args
}
exit $LASTEXITCODE
