# Dedicated Server PC Setup

This runbook is for moving `Stock_GPT_Analysis_Server1` to a new Windows PC and proving the Kiwoom legacy path safely.

## Goal

The server PC should prove this chain:

```text
FastAPI server readiness
-> py37_32 Kiwoom runtime readiness
-> Kiwoom login and realtime registration
-> JSONL tick spool
-> Python 3.11 import into SQLite
-> status visible through server tools/UI
```

Do not enable live order execution during this setup.

## 1. Clone And Configure

```powershell
cd C:\Users\lmhk2\PycharmProjects
git clone https://github.com/lmhk0917-cloud/Stock_GPT_Analysis_Server1.git
cd .\Stock_GPT_Analysis_Server1
Copy-Item .env.local.example .env.local
notepad .env.local
```

Fill in local-only values:

- `OPENAI_API_KEY`
- `ADMIN_API_TOKEN`
- `CREDENTIAL_MASTER_KEY`
- keep `ENABLE_ORDER_API=0`

## 2. Create Server Runtime

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe create -y -n stock_server_py311 python=3.11
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python -m pip install -r requirements.txt
```

Run server PC preflight:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\server_pc_preflight.py
```

Then run the offline operations check:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\ops_check.py
```

## 3. Prepare Kiwoom Runtime

Install Kiwoom OpenAPI+ and make sure `C:\OpenAPI\khopenapi.ocx` exists.

Create or restore the 32-bit runtime:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe create -y -n py37_32 python=3.7
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n py37_32 python -m pip install -r requirements-kiwoom-legacy.txt
```

Check the runtime:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n py37_32 python tools\kiwoom_runtime_check.py
```

Expected strong signals:

```text
KIWOOM_PYTHON_32BIT=OK
PYQT_QAX_IMPORT=OK
KIWOOM_OCX_CREATE=OK
```

If `KIWOOM_OCX_CREATE=WARN`, fix OpenAPI installation or OCX registration before live testing.

## 4. First Live Probe

Run only one Kiwoom process at a time. Do not run a personal-project collector and this server probe together.

For a login/register smoke test:

```powershell
.\scripts\run_kiwoom_live_probe.ps1 -Codes "005930,000660" -Seconds 60
```

For a regular-session proof that must receive ticks:

```powershell
.\scripts\run_kiwoom_live_probe.ps1 -Codes "005930,000660" -Seconds 60 -RequireTicks
```

Success criteria during market hours:

```text
KIWOOM_WORKER_LOGIN_RESULT=0
KIWOOM_WORKER_REALTIME_REGISTER_RESULT=0
KIWOOM_WORKER_SAVED_TICK_COUNT > 0
KIWOOM_LEGACY_TICK_COUNT increases after import
KIWOOM_LIVE_PROBE_RESULT=PASS
```

After-hours login success with zero ticks is useful but not a full market-data proof.

## 5. Start Server

```powershell
.\scripts\run_fastapi_server.ps1
```

Open:

```text
http://127.0.0.1:8000/admin/ui
http://127.0.0.1:8000/client/ui
```

## 6. External Access Later

Only after local proof:

1. Bind the server for LAN or tunnel use.
2. Add Windows firewall rule if using LAN access.
3. Prefer Cloudflare Tunnel + Access for internet exposure.
4. Add backup/autostart after the live Kiwoom path is stable.

## Rules

- Keep `ENABLE_ORDER_API=0`.
- Keep `.env.local` local and uncommitted.
- Do not run multiple `conda run` checks in parallel on this Windows setup.
- Do not run two Kiwoom QAxWidget processes at the same time.
- Treat server PC validation as incomplete until a regular-session tick-growth proof passes.
