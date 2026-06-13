$ErrorActionPreference = "Stop"

param(
    [string]$Codes = "005930,000660",
    [int]$Seconds = 60,
    [switch]$RequireTicks,
    [switch]$RequireExistingLogin
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$LogDir = Join-Path $ProjectRoot "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogPath = Join-Path $LogDir "kiwoom_live_probe_$Timestamp.log"

Start-Transcript -Path $LogPath -Force | Out-Null
try {
    Write-Output "KIWOOM_LIVE_PROBE_PROJECT_ROOT=$ProjectRoot"
    Write-Output "KIWOOM_LIVE_PROBE_CODES=$Codes"
    Write-Output "KIWOOM_LIVE_PROBE_SECONDS=$Seconds"
    Write-Output "KIWOOM_LIVE_PROBE_REQUIRE_TICKS=$([int]$RequireTicks.IsPresent)"
    Write-Output "KIWOOM_LIVE_PROBE_REQUIRE_EXISTING_LOGIN=$([int]$RequireExistingLogin.IsPresent)"
    Write-Output "KIWOOM_LIVE_PROBE_LOG=$LogPath"

    & C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n py37_32 python tools\kiwoom_runtime_check.py

    $workerArgs = @(
        "run", "--no-capture-output", "-n", "py37_32",
        "python", "-m", "legacy.kiwoom_worker",
        "--codes", $Codes,
        "--seconds", "$Seconds"
    )
    if ($RequireTicks.IsPresent) {
        $workerArgs += "--require-ticks"
    }
    if ($RequireExistingLogin.IsPresent) {
        $workerArgs += "--require-existing-login"
    }

    & C:\Users\lmhk2\anaconda3\Scripts\conda.exe @workerArgs
    $WorkerExit = $LASTEXITCODE
    Write-Output "KIWOOM_LIVE_PROBE_WORKER_EXIT=$WorkerExit"

    & C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\import_kiwoom_spool.py
    & C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\kiwoom_spool_status.py

    if ($WorkerExit -ne 0) {
        exit $WorkerExit
    }
    Write-Output "KIWOOM_LIVE_PROBE_RESULT=PASS"
}
finally {
    Stop-Transcript | Out-Null
}
