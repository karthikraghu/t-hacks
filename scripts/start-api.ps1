$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "Python environment missing. Create .venv and install services/api/requirements.txt first."
}

Set-Location $repoRoot
& $venvPython -m uvicorn services.api.app.main:app --reload --host 127.0.0.1 --port 8000

