"""Import Kiwoom legacy-worker JSONL events into the server database."""

import json
from pathlib import Path

from core.database import dumps_json, utc_now


def import_spool(conn, spool_path):
    path = Path(spool_path)
    if not path.exists():
        return {"read": 0, "inserted": 0, "duplicates": 0, "invalid": 0}

    stats = {"read": 0, "inserted": 0, "duplicates": 0, "invalid": 0}
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            stats["read"] += 1
            try:
                event = json.loads(line)
                tick = event["tick"]
                if event.get("schema") != "kiwoom_tick_v1":
                    raise ValueError("unsupported schema")
                if not event.get("source_event_id") or not tick.get("code") or not tick.get("received_at"):
                    raise ValueError("missing required fields")
                inserted = _insert_tick(conn, event, tick)
                stats["inserted" if inserted else "duplicates"] += 1
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                stats["invalid"] += 1
    conn.commit()
    return stats


def _insert_tick(conn, event, tick):
    cur = conn.execute(
        """
        INSERT OR IGNORE INTO kiwoom_legacy_ticks(
          source_event_id, market, code, trade_time, price, change_rate, acc_volume,
          tick_volume, open_price, high_price, low_price, strength, received_at,
          imported_at, raw_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["source_event_id"],
            event.get("market", "KRX"),
            tick["code"],
            tick.get("trade_time"),
            tick.get("price"),
            tick.get("change_rate"),
            tick.get("acc_volume"),
            tick.get("tick_volume"),
            tick.get("open_price"),
            tick.get("high_price"),
            tick.get("low_price"),
            tick.get("strength"),
            tick["received_at"],
            utc_now(),
            dumps_json(event),
        ),
    )
    return cur.rowcount > 0
