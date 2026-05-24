"""Validate local environment variables for server operation."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.config import (
    ADMIN_API_TOKEN,
    CREDENTIAL_MASTER_KEY,
    ENABLE_ORDER_API,
    OPENAI_API_KEY,
    REQUIRE_ORDER_CONFIRMATION,
    get_db_path,
)


def mask(value):
    if not value:
        return "MISSING"
    return "SET"


def main():
    checks = {
        "CREDENTIAL_MASTER_KEY": bool(CREDENTIAL_MASTER_KEY),
        "ADMIN_API_TOKEN": bool(ADMIN_API_TOKEN),
        "OPENAI_API_KEY": bool(OPENAI_API_KEY),
        "DB_PARENT_EXISTS": get_db_path().parent.exists(),
    }
    print("DB_PATH={}".format(get_db_path()))
    print("ENABLE_ORDER_API={}".format(int(ENABLE_ORDER_API)))
    print("REQUIRE_ORDER_CONFIRMATION={}".format(int(REQUIRE_ORDER_CONFIRMATION)))
    print("CREDENTIAL_MASTER_KEY={}".format(mask(CREDENTIAL_MASTER_KEY)))
    print("ADMIN_API_TOKEN={}".format(mask(ADMIN_API_TOKEN)))
    print("OPENAI_API_KEY={}".format(mask(OPENAI_API_KEY)))
    for name, ok in checks.items():
        print("{}={}".format(name, "OK" if ok else "WARN"))

    if ENABLE_ORDER_API:
        print("ORDER_API_WARNING=ENABLE_ORDER_API is on")


if __name__ == "__main__":
    main()
