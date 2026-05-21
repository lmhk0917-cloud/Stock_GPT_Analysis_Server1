"""Kiwoom adapter boundary.

The existing personal project uses Windows-only QAxWidget code. That dependency
is intentionally isolated in ``legacy/kiwoom_worker.py`` instead of being
imported by the 64-bit server runtime.
"""

from market_data.adapters.base import MarketDataAdapter


class KiwoomAdapter(MarketDataAdapter):
    provider = "kiwoom"

    def __init__(self):
        raise RuntimeError(
            "Kiwoom OpenAPI+ requires the isolated py37_32 legacy worker. "
            "Do not load QAxWidget in the main server process."
        )
