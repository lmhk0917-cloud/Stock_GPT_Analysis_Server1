"""Provider adapter interface notes.

Concrete adapters should return provider-neutral symbol and OHLCV dictionaries.
Kiwoom/QAxWidget and KIS REST code belongs behind this boundary.
"""


class MarketDataAdapter:
    provider = "base"

    def list_symbols(self):
        raise NotImplementedError

    def fetch_ohlcv(self, market, code, timeframe="1m", limit=80):
        raise NotImplementedError

    def get_quote(self, market, code):
        raise NotImplementedError

    def place_order(self, order_request, credentials):
        raise NotImplementedError
