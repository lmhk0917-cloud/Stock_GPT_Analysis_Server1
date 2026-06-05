# Kiwoom Legacy Integration Runbook

This document describes how the server project integrates Kiwoom OpenAPI+ without letting its legacy runtime leak into the main backend.

## Design Goal

Kiwoom OpenAPI+ requires a Windows GUI/COM environment and 32-bit Python. The server should not inherit that constraint. The stable boundary is:

```text
py37_32 Kiwoom worker -> JSONL spool -> Python 3.11 importer -> SQLite -> FastAPI/API UI
```

This keeps the FastAPI server deployable on modern Python while still allowing a Windows server PC to collect Kiwoom realtime data.

## What Was Borrowed From Personal Ver

The personal project proved several useful operating rules:

- Treat Kiwoom login, realtime registration, and tick persistence as separate checks.
- Do not run multiple Kiwoom/QAxWidget tests back-to-back when the goal is a regular-session validation.
- After-hours login success is useful, but it does not prove regular-session `OnReceiveRealData` growth.
- GPT should review risk/reward and missing context; deterministic code should collect data, calculate features, store logs, and enforce order gates.
- Small fixed watchlists such as `005930` and `000660` are better for deep validation than broad screening during early server hardening.

The server version implements those lessons with a smaller, adapter-friendly contract rather than copying the personal app's full GUI and scheduler.

## Runtime Split

Main server:

- Environment: `stock_server_py311`
- Python: 3.11 64-bit
- Responsibilities: API, UI, user/session state, encryption, OpenAI calls, spool import, SQLite storage

Kiwoom worker:

- Environment: `py37_32`
- Python: 3.7 32-bit
- Responsibilities: create `QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")`, login, register realtime codes, write JSONL events

The worker does not import the server package and does not write directly to the server database.

## Spool Event Contract

Each line in `data\kiwoom_spool\kiwoom_ticks.jsonl` is one JSON object:

```json
{
  "schema": "kiwoom_tick_v1",
  "source_event_id": "unique-event-id",
  "market": "KRX",
  "tick": {
    "code": "005930",
    "trade_time": "090001",
    "price": 70000,
    "change_rate": 1.23,
    "acc_volume": 123456,
    "tick_volume": 100,
    "open_price": 69000,
    "high_price": 70500,
    "low_price": 68800,
    "strength": 110.5,
    "received_at": "2026-06-06 09:00:01.000000"
  }
}
```

`source_event_id` is unique. The importer uses `INSERT OR IGNORE`, so repeated imports are idempotent.

## Offline Validation

Run this before any live Kiwoom work:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\kiwoom_spool_smoke_test.py
```

Expected output includes:

```text
KIWOOM_SPOOL_SMOKE_TEST_OK
```

Then run the broader server check:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\ops_check.py
```

## Live Worker Procedure

Use this only on the Windows machine where Kiwoom OpenAPI+ is installed and the `py37_32` environment is configured.

```powershell
.\scripts\run_kiwoom_legacy_worker.ps1 --codes 005930,000660 --seconds 60
```

Then import:

```powershell
.\scripts\import_kiwoom_spool.ps1
```

Check imported status:

```powershell
C:\Users\lmhk2\anaconda3\Scripts\conda.exe run --no-capture-output -n stock_server_py311 python tools\kiwoom_spool_status.py
```

Success criteria during a regular session:

```text
KIWOOM_WORKER_LOGIN_RESULT=0
KIWOOM_WORKER_REALTIME_REGISTER_RESULT=0
KIWOOM_WORKER_SAVED_TICK_COUNT > 0
KIWOOM_LEGACY_TICK_COUNT increases after import
```

If login succeeds after hours but `KIWOOM_WORKER_SAVED_TICK_COUNT=0`, treat it as an incomplete market-data proof, not as a server failure.

## Server PC Stage

The next meaningful live milestone is a dedicated server PC because Kiwoom's GUI login, security modules, Windows session state, and market-hours tests are environment-sensitive.

Recommended order:

1. Clone this repository.
2. Recreate `stock_server_py311`.
3. Recreate or install `py37_32` with Kiwoom dependencies.
4. Run `tools\ops_check.py`.
5. Install Kiwoom OpenAPI+ and verify OCX creation.
6. Run the legacy worker during a regular market session.
7. Import the spool and confirm tick growth through `tools\kiwoom_spool_status.py`.
8. Only after local live proof, add Cloudflare Tunnel and Access.

## Risk Boundaries

- Do not run two Kiwoom workers at the same time.
- Do not run broad analysis before minimal tick growth is confirmed.
- Do not enable live order execution during data-collection validation.
- Keep `ENABLE_ORDER_API=0` until provider-specific order behavior is reviewed.
- Keep OpenAI prompts focused on analysis and review, not autonomous execution.
