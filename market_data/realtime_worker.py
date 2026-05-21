"""Mock-first analysis worker for the server MVP."""

import pandas as pd

from analysis.event_detector import detect_gpt_events
from analysis.gpt_analyzer import GPTAnalyzer
from analysis.indicators import add_indicators, summarize_for_gpt
from core.audit_store import AuditStore
from delivery.notifier import UserNotifier
from market_data.backfill import fetch_and_store_latest_bars
from market_data.adapters.mock_adapter import MockMarketDataAdapter


def run_once(conn, user_store, adapter=None, use_gpt=False):
    adapter = adapter or MockMarketDataAdapter()
    audit_store = AuditStore(conn)
    symbols = user_store.unique_enabled_symbols() or adapter.list_symbols()
    fetch_and_store_latest_bars(adapter, audit_store, symbols)

    analyzer = GPTAnalyzer() if use_gpt else None
    notifier = UserNotifier(conn)
    results = []

    for symbol in symbols:
        bars = adapter.fetch_ohlcv(symbol["market"], symbol["code"], limit=80)
        df = pd.DataFrame(bars)
        df = df.rename(columns={"timestamp": "received_at", "close": "price", "volume": "tick_volume"})
        ohlcv = pd.DataFrame(bars).set_index(pd.to_datetime(df["received_at"]))
        ohlcv = ohlcv[["open", "high", "low", "close", "volume"]]
        indicators = add_indicators(ohlcv)
        timeframe_summary = summarize_for_gpt(symbol["code"], symbol["name"], indicators)
        summary = {
            "market": symbol["market"],
            "code": symbol["code"],
            "name": symbol["name"],
            "timeframes": {"1m": timeframe_summary},
        }
        events = detect_gpt_events(summary)
        summary["events"] = events
        gpt_result = analyzer.analyze([summary]) if analyzer else "mock analysis: shared result generated without GPT call"
        analysis_id = audit_store.save_analysis_result(
            symbol["market"],
            symbol["code"],
            summary,
            gpt_result=gpt_result,
            model=getattr(analyzer, "last_model", "mock"),
        )
        for event in events:
            audit_store.save_event(symbol["market"], symbol["code"], event, summary)
        notifications = notifier.notify_matching_users(summary, events)
        results.append({
            "analysis_id": analysis_id,
            "symbol": symbol,
            "events": events,
            "notifications": notifications,
        })

    return results
