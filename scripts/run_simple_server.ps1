$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $env:CREDENTIAL_MASTER_KEY) {
    $env:CREDENTIAL_MASTER_KEY = "local-dev-change-me"
}

python -m server.simple_server --host 127.0.0.1 --port 8765
