$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

if (-not $env:CREDENTIAL_MASTER_KEY) {
    $env:CREDENTIAL_MASTER_KEY = "local-dev-change-me"
}

uvicorn server.api:app --host 127.0.0.1 --port 8000 --reload
