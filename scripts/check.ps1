param(
    [string]$Python = "python",
    [string]$EnvironmentRoot = $env:MEETING_ENV_ROOT
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    if ($EnvironmentRoot) { $env:MEETING_ENV_ROOT = $EnvironmentRoot }
    & $Python -m ruff check .
    if ($LASTEXITCODE -ne 0) { throw "Ruff lint failed." }
    & $Python -m ruff format --check .
    if ($LASTEXITCODE -ne 0) { throw "Ruff formatting failed." }
    & npm.cmd run lint:js
    if ($LASTEXITCODE -ne 0) { throw "JavaScript lint failed." }
    $testTemp = Join-Path $projectRoot (".cache/check-" + [guid]::NewGuid().ToString("N"))
    & $Python -m pytest tests -q -p no:cacheprovider --basetemp $testTemp --tb=short
    if ($LASTEXITCODE -ne 0) { throw "Tests failed." }
    Write-Host "All pre-commit checks passed."
}
finally {
    Pop-Location
}
