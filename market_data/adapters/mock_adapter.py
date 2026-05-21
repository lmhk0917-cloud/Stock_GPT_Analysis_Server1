"""Deterministic mock market data for offline development and tests."""

import math
from datetime import datetime, timedelta

from market_data.adapters.base import MarketDataAdapter


class MockMarketDataAdapter(MarketDataAdapter):
    provider = "mock"

    def __init__(self):
        self._symbols = [
            {"market": "KRX", "code": "005930", "name": "Samsung Electronics"},
            {"market": "KRX", "code": "000660", "name": "SK hynix"},
            {"market": "KRX", "code": "035420", "name": "NAVER"},
        ]

    def list_symbols(self):
        return list(self._symbols)

    def fetch_ohlcv(self, market, code, timeframe="1m", limit=80):
        if timeframe != "1m":
            raise ValueError("mock adapter currently supports 1m timeframe only")

        base_price = 60000 + (sum(ord(ch) for ch in code) % 150) * 100
        start = datetime.utcnow().replace(second=0, microsecond=0) - timedelta(minutes=limit)
        bars = []

        for idx in range(limit):
            wave = math.sin(idx / 5.0) * 250
            trend = idx * 12
            close = base_price + trend + wave
            if idx >= limit - 4:
                close += (idx - (limit - 5)) * 180
            open_price = close - math.sin(idx / 3.0) * 80
            high = max(open_price, close) + 120 + (idx % 4) * 15
            low = min(open_price, close) - 110 - (idx % 3) * 10
            volume = 1000 + (idx % 12) * 170
            if idx == limit - 2:
                volume *= 4

            bars.append({
                "timestamp": (start + timedelta(minutes=idx)).isoformat() + "Z",
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": round(volume, 2),
            })

        return bars

    def get_quote(self, market, code):
        symbol = next((item for item in self._symbols if item["market"] == market and item["code"] == code), None)
        if not symbol:
            raise ValueError("unknown mock symbol: {} {}".format(market, code))
        latest = self.fetch_ohlcv(market, code, limit=2)[-1]
        return {
            "provider": self.provider,
            "market": market,
            "code": code,
            "name": symbol["name"],
            "price": latest["close"],
            "timestamp": latest["timestamp"],
        }

    def place_order(self, order_request, credentials=None):
        return {
            "provider": self.provider,
            "status": "mock_not_executed",
            "order_request": order_request,
        }
