# FX Provider Strategy

The server evidence pack includes an `fx_context` slot so GPT can discuss FX risk without hardcoding one data source.

## Provider Order

1. Broker REST API when the final broker is selected.
2. Paid/contracted near-realtime FX API if stronger reliability is needed.
3. ECOS or other official daily/reference data for non-realtime context.
4. Manual `.env.local` value as a temporary private-test fallback.

## Current Fallback

Set these in `.env.local`:

```text
FX_USD_KRW=1375.2
FX_USD_KRW_SOURCE=manual_env
FX_USD_KRW_ASOF=2026-06-14T09:00:00Z
FX_USD_KRW_RELIABILITY=manual_reference
```

If `FX_USD_KRW` is missing, the evidence pack marks FX as missing and GPT must say that FX evidence is unavailable.

## Evidence Contract

```json
{
  "pair": "USD/KRW",
  "value": 1375.2,
  "source": "manual_env",
  "asof": "2026-06-14T09:00:00Z",
  "reliability": "manual_reference",
  "missing": false
}
```

## Rule

GPT may discuss FX only as a supporting risk factor unless the source is fresh and reliable. If FX is missing or stale, it should explicitly say so.
