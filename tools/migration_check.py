"""Show migration application status for the configured SQLite DB."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from core.database import init_db
from core.migrations import migration_status


def main():
    conn = init_db()
    statuses = migration_status(conn)
    for item in statuses:
        print("{}={}".format(item["version"], "APPLIED" if item["applied"] else "PENDING"))
    if not statuses:
        print("NO_MIGRATIONS_FOUND")
        raise SystemExit(1)
    if not all(item["applied"] for item in statuses):
        raise SystemExit(1)
    print("MIGRATION_CHECK_OK")


if __name__ == "__main__":
    main()
