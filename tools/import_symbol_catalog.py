"""Import a CSV symbol catalog into market_symbols."""

import argparse
import csv
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.audit_store import AuditStore
from core.database import init_db


def main():
    parser = argparse.ArgumentParser(description="Import symbols from CSV into market_symbols.")
    parser.add_argument("--file", required=True, help="CSV path with at least code and name columns")
    parser.add_argument("--market", default="KRX")
    parser.add_argument("--provider", default="catalog_csv")
    parser.add_argument("--encoding", default="utf-8-sig")
    args = parser.parse_args()

    conn = init_db()
    count = 0
    try:
        audit = AuditStore(conn)
        with open(args.file, "r", encoding=args.encoding, newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                code = _pick(row, "code", "종목코드", "단축코드", "ticker")
                name = _pick(row, "name", "종목명", "한글 종목명", "kor_name")
                market = _pick(row, "market", "시장") or args.market
                currency = _pick(row, "currency", "통화") or "KRW"
                if not code or not name:
                    continue
                audit.upsert_symbol(
                    market.strip().upper(),
                    str(code).strip().zfill(6) if str(code).strip().isdigit() else str(code).strip(),
                    name.strip(),
                    currency=currency.strip().upper(),
                    provider=args.provider,
                    enabled=True,
                )
                count += 1
    finally:
        conn.close()
    print("SYMBOL_CATALOG_IMPORTED={}".format(count))


def _pick(row, *keys):
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


if __name__ == "__main__":
    main()
