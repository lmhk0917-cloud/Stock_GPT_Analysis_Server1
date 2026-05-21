"""Application configuration for the server-style multiuser MVP."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_PATH = DATA_DIR / "stock_gpt_analysis_server1.db"

APP_NAME = "Stock_GPT_Analysis_Server1"
DEFAULT_MARKET = "KRX"
DEFAULT_PROVIDER = "mock"

GPT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
GPT_MAX_TOKENS = int(os.getenv("GPT_MAX_TOKENS", "1600"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ADMIN_API_TOKEN = os.getenv("ADMIN_API_TOKEN", "")
CREDENTIAL_MASTER_KEY = os.getenv("CREDENTIAL_MASTER_KEY", "")
ENABLE_ORDER_API = os.getenv("ENABLE_ORDER_API", "0") in ("1", "true", "True")
REQUIRE_ORDER_CONFIRMATION = os.getenv("REQUIRE_ORDER_CONFIRMATION", "1") not in ("0", "false", "False")
ORDER_CONFIRMATION_TEXT = os.getenv("ORDER_CONFIRMATION_TEXT", "주문 위험을 확인했고 실행을 승인합니다")

ENABLE_NOTIFICATIONS = os.getenv("ENABLE_NOTIFICATIONS", "1") not in ("0", "false", "False")
NOTIFICATION_CHANNELS = [
    channel.strip()
    for channel in os.getenv("NOTIFICATION_CHANNELS", "console").split(",")
    if channel.strip()
]
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_TIMEOUT_SEC = int(os.getenv("TELEGRAM_TIMEOUT_SEC", "8"))
TELEGRAM_MAX_MESSAGE_CHARS = int(os.getenv("TELEGRAM_MAX_MESSAGE_CHARS", "3500"))

EVENT_RSI_LOW = float(os.getenv("EVENT_RSI_LOW", "30"))
EVENT_RSI_HIGH = float(os.getenv("EVENT_RSI_HIGH", "70"))
EVENT_VOLUME_RATIO = float(os.getenv("EVENT_VOLUME_RATIO", "1.8"))
EVENT_BOX_HIGH_POSITION = float(os.getenv("EVENT_BOX_HIGH_POSITION", "0.85"))
EVENT_BOX_LOW_POSITION = float(os.getenv("EVENT_BOX_LOW_POSITION", "0.15"))
EVENT_VWAP_NEAR_PCT = float(os.getenv("EVENT_VWAP_NEAR_PCT", "0.4"))
EVENT_CONSECUTIVE_BARS = int(os.getenv("EVENT_CONSECUTIVE_BARS", "3"))
EVENT_ORDERBOOK_IMBALANCE = float(os.getenv("EVENT_ORDERBOOK_IMBALANCE", "0.35"))


def get_db_path():
    """Return the configured DB path and ensure its parent exists."""
    raw_path = os.getenv("STOCK_SERVER_DB_PATH")
    db_path = Path(raw_path) if raw_path else DEFAULT_DB_PATH
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path
