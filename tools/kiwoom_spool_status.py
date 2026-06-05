"""Print imported Kiwoom legacy tick status from the server database."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.database import init_db


def main():
    conn = init_db()
    try:
        total, latest = conn.execute(
            "SELECT COUNT(*), MAX(received_at) FROM kiwoom_legacy_ticks"
        ).fetchone()
        code_rows = conn.execute(
            """
            SELECT code, COUNT(*) AS tick_count, MAX(received_at) AS latest_received_at
            FROM kiwoom_legacy_ticks
            GROUP BY code
            ORDER BY latest_received_at DESC, code
            LIMIT 20
            """
        ).fetchall()
        latest_rows = conn.execute(
            """
            SELECT code, trade_time, price, tick_volume, received_at, imported_at
            FROM kiwoom_legacy_ticks
            ORDER BY received_at DESC, id DESC
            LIMIT 5
            """
        ).fetchall()
    finally:
        conn.close()

    print("KIWOOM_LEGACY_TICK_COUNT={}".format(total))
    print("KIWOOM_LEGACY_LATEST_RECEIVED_AT={}".format(latest or ""))
    print("KIWOOM_LEGACY_CODE_COUNT={}".format(len(code_rows)))
    for row in code_rows:
        print(
            "KIWOOM_LEGACY_CODE_STATUS={},ticks:{},latest:{}".format(
                row["code"],
                row["tick_count"],
                row["latest_received_at"],
            )
        )
    for row in latest_rows:
        print(
            "KIWOOM_LEGACY_LATEST_TICK={},time:{},price:{},volume:{},received:{},imported:{}".format(
                row["code"],
                row["trade_time"] or "",
                row["price"] if row["price"] is not None else "",
                row["tick_volume"] if row["tick_volume"] is not None else "",
                row["received_at"],
                row["imported_at"],
            )
        )
    print("KIWOOM_LEGACY_STATUS_OK")


if __name__ == "__main__":
    main()
