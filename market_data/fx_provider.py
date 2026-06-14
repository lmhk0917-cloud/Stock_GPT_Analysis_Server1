"""FX context helpers for GPT evidence packs.

The first implementation is intentionally manual/env based. Later this can be
replaced by KIS REST, ECOS, or a paid FX data provider without changing the
evidence-pack shape.
"""

import os

from core.database import utc_now


def get_fx_snapshot():
    value = _to_float(os.getenv("FX_USD_KRW"))
    source = os.getenv("FX_USD_KRW_SOURCE", "manual_env")
    asof = os.getenv("FX_USD_KRW_ASOF") or utc_now()
    reliability = os.getenv("FX_USD_KRW_RELIABILITY", "manual_or_missing")
    return {
        "pair": "USD/KRW",
        "value": value,
        "source": source,
        "asof": asof if value is not None else None,
        "reliability": reliability if value is not None else "missing",
        "missing": value is None,
    }


def _to_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
