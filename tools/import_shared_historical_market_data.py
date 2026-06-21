"""Import shared daily historical data into the server market_prices table."""

import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.database import init_db


DEFAULT_PACKAGE = (
    r"C:\Users\lmhk2\Documents\New project\market_data_exports\daily_history"
    r"\yahoo_finance_10y_ai_semiconductor_1d\shared"
    r"\historical_market_data_v1_daily_kr_us_ai_semiconductor.json"
)


def main():
    parser = argparse.ArgumentParser(description="Import shared daily historical prices into Stock GPT server.")
    parser.add_argument("--file", default=DEFAULT_PACKAGE)
    parser.add_argument("--markets", default="KRX,US")
    args = parser.parse_args()

    package = load_package(args.file)
    validate_daily_package(package)
    markets = set(item.strip().upper() for item in args.markets.split(",") if item.strip())
    conn = init_db()
    try:
        inserted = import_bars(conn, package, markets)
    finally:
        conn.close()
    print("SHARED_HISTORICAL_SERVER_IMPORT_STATUS=ok")
    print("SHARED_HISTORICAL_SERVER_IMPORT_FILE={}".format(args.file))
    print("SHARED_HISTORICAL_SERVER_IMPORT_TIMEFRAME=1d")
    print("SHARED_HISTORICAL_SERVER_IMPORT_TICKS_CREATED=0")
    print("SHARED_HISTORICAL_SERVER_IMPORT_ROWS={}".format(inserted))


def load_package(path):
    if not os.path.exists(path):
        raise RuntimeError("Shared historical package not found: {}".format(path))
    with open(path, "r", encoding="utf-8") as fp:
        return json.load(fp)


def validate_daily_package(package):
    if package.get("schema") != "historical_market_data_v1":
        raise RuntimeError("Unsupported package schema: {}".format(package.get("schema")))
    resolution = package.get("resolution") or {}
    if resolution.get("timeframe") != "1d":
        raise RuntimeError("Only 1d shared history is supported; got {}".format(resolution.get("timeframe")))
    if resolution.get("intraday_source") or resolution.get("tick_source"):
        raise RuntimeError("Refusing to import package that claims intraday/tick source.")


def import_bars(conn, package, markets):
    rows = []
    for item in package.get("bars") or []:
        if str(item.get("market") or "").upper() not in markets:
            continue
        rows.append((
            item.get("market"),
            str(item.get("code") or ""),
            "1d",
            item.get("bar_time") or "{} 00:00:00".format(item.get("date")),
            item.get("open"),
            item.get("high"),
            item.get("low"),
            item.get("close"),
            item.get("volume") or 0,
            "shared_yahoo_history_daily",
        ))
    conn.executemany(
        """
        INSERT OR REPLACE INTO market_prices (
          market, code, timeframe, timestamp, open, high, low, close, volume, provider
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)


if __name__ == "__main__":
    main()
