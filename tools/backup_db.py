"""Create a timestamped SQLite backup using the sqlite backup API."""

import argparse
from datetime import datetime
import os
from pathlib import Path
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.config import get_db_path


def backup_database(source_path=None, backup_dir=None):
    source = Path(source_path) if source_path else get_db_path()
    if not source.exists():
        raise FileNotFoundError("DB does not exist: {}".format(source))

    target_dir = Path(backup_dir) if backup_dir else source.parent / "backups"
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = target_dir / "{}_{}.db".format(source.stem, stamp)

    src_conn = sqlite3.connect(str(source))
    try:
        dst_conn = sqlite3.connect(str(target))
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()
    return target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=None)
    parser.add_argument("--backup-dir", default=None)
    args = parser.parse_args()
    target = backup_database(args.source, args.backup_dir)
    print("DB_BACKUP_OK path={}".format(target))


if __name__ == "__main__":
    main()
