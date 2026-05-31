"""Offline smoke test for the Kiwoom legacy JSONL spool boundary."""

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.database import init_db
from legacy.kiwoom_spool import import_spool


def main():
    temp_dir = tempfile.mkdtemp(prefix="stock_server_kiwoom_spool_")
    db_path = os.path.join(temp_dir, "kiwoom_spool.db")
    spool_path = os.path.join(temp_dir, "kiwoom_ticks.jsonl")
    event = {
        "schema": "kiwoom_tick_v1",
        "source_event_id": "offline-smoke-event-1",
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
            "received_at": "2026-05-31 09:00:01.000000",
        },
    }
    with open(spool_path, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        handle.write("not-json\n")

    conn = init_db(db_path)
    try:
        first = import_spool(conn, spool_path)
        second = import_spool(conn, spool_path)
        row = conn.execute(
            "SELECT code, price, tick_volume FROM kiwoom_legacy_ticks WHERE source_event_id = ?",
            ("offline-smoke-event-1",),
        ).fetchone()
        count = conn.execute("SELECT COUNT(*) FROM kiwoom_legacy_ticks").fetchone()[0]
    finally:
        conn.close()

    checks = {
        "first_import": first == {"read": 3, "inserted": 1, "duplicates": 1, "invalid": 1},
        "idempotent_import": second == {"read": 3, "inserted": 0, "duplicates": 2, "invalid": 1},
        "tick_persisted": count == 1 and row["code"] == "005930" and row["price"] == 70000,
    }
    for name, ok in checks.items():
        print("{}={}".format(name, "OK" if ok else "FAIL"))
    if not all(checks.values()):
        raise SystemExit(1)
    print("KIWOOM_SPOOL_SMOKE_TEST_OK")


if __name__ == "__main__":
    main()
