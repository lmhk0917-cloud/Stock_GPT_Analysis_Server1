$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

& C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n py37_32 python -m legacy.kiwoom_worker @args
