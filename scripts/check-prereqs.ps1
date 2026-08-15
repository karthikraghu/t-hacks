$ErrorActionPreference = "Stop"
$commands = @("node", "npm")
$missing = @()

foreach ($name in $commands) {
    $command = Get-Command $name -ErrorAction SilentlyContinue
    if ($null -eq $command) {
        Write-Host "[missing] $name" -ForegroundColor Red
        $missing += $name
    } else {
        Write-Host "[ok]      $name -> $($command.Source)" -ForegroundColor Green
    }
}

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
$venvManim = Join-Path $repoRoot ".venv\Scripts\manim.exe"
if (-not (Test-Path -LiteralPath $venvPython)) { $missing += "workspace Python" }
if (-not (Test-Path -LiteralPath $venvManim)) { $missing += "workspace Manim" }
$latex = Get-Command latex -ErrorAction SilentlyContinue
$localLatex = Join-Path $env:LOCALAPPDATA "Programs\MiKTeX\miktex\bin\x64\latex.exe"
if ($null -eq $latex -and -not (Test-Path -LiteralPath $localLatex)) { $missing += "MiKTeX/LaTeX" }

if ($missing.Count -gt 0) {
    throw "Missing prerequisites: $($missing -join ', ')"
}

Write-Host "Local runtime prerequisites found." -ForegroundColor Green
