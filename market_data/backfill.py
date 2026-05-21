"""Provider-neutral backfill helpers."""


def fetch_and_store_latest_bars(adapter, audit_store, symbols, timeframe="1m", limit=80):
    for symbol in symbols:
        audit_store.upsert_symbol(
            symbol["market"],
            symbol["code"],
            symbol["name"],
            provider=getattr(adapter, "provider", "unknown"),
        )
        bars = adapter.fetch_ohlcv(symbol["market"], symbol["code"], timeframe=timeframe, limit=limit)
        for bar in bars:
            audit_store.save_price_bar(
                symbol["market"],
                symbol["code"],
                timeframe,
                bar,
                provider=getattr(adapter, "provider", "unknown"),
            )
