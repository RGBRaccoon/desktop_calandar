param(
    [string]$Report = '.local/test-results.xml'
)
$ErrorActionPreference = 'Stop'
$calendarPython = Join-Path $PSScriptRoot '../.venv/Scripts/python.exe'
function Invoke-Check {
    param([string[]]$Arguments)
    & $calendarPython @Arguments
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
Invoke-Check -Arguments @('-m', 'ruff', 'check', 'src', 'tests', 'scripts', 'run.py')
Invoke-Check -Arguments @('-m', 'ruff', 'format', '--check', 'src', 'tests', 'scripts', 'run.py')
Invoke-Check -Arguments @('-m', 'pyright')
Invoke-Check -Arguments @('-m', 'pytest', '-q', "--junitxml=$Report")
