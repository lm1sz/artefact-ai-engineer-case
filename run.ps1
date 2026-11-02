# Prefer the project environment, then this PC's bundled runtime, then installed Python.
$ErrorActionPreference = 'Stop'
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$bundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Test-Path -LiteralPath $projectPython) {
    $agentPython = $projectPython
} elseif (Test-Path -LiteralPath $bundledPython) {
    $agentPython = $bundledPython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $agentPython = (Get-Command python).Source
} else {
    throw 'Create .venv and install the project using the commands in README.md.'
}
Push-Location -LiteralPath $PSScriptRoot
try {
    & $agentPython -X utf8 -u -m chatbot @args
    $agentExitCode = $LASTEXITCODE
} finally {
    Pop-Location
}
exit $agentExitCode
