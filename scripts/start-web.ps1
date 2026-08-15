$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$webRoot = Join-Path $repoRoot "apps\web"

if (-not (Test-Path -LiteralPath (Join-Path $webRoot "node_modules"))) {
    throw "Frontend dependencies missing. Run npm install in apps/web first."
}

Set-Location $webRoot
npm run dev

