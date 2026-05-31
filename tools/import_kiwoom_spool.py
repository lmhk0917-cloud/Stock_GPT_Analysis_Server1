"""Import JSONL ticks emitted by the isolated Kiwoom legacy worker."""

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.database import init_db
from legacy.kiwoom_spool import import_spool


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--spool-path",
        default=os.path.join(ROOT, "data", "kiwoom_spool", "kiwoom_ticks.jsonl"),
    )
    return parser.parse_args()


def main():
    args = parse_args()
    conn = init_db()
    try:
        stats = import_spool(conn, args.spool_path)
    finally:
        conn.close()
    for key in ("read", "inserted", "duplicates", "invalid"):
        print("KIWOOM_SPOOL_{}={}".format(key.upper(), stats[key]))
    print("KIWOOM_SPOOL_IMPORT_OK")


if __name__ == "__main__":
    main()
