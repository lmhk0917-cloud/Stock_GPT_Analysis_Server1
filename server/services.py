"""Application service layer used by API and CLI tools."""

from core.audit_store import AuditStore
from core.database import init_db
from core.user_store import UserStore
from market_data.realtime_worker import run_once


def bootstrap_demo_data(conn):
    users = UserStore(conn)
    alice_id = users.upsert_user("alice", "Alice", telegram_chat_id=None)
    bob_id = users.upsert_user("bob", "Bob", telegram_chat_id=None)

    users.add_watchlist(alice_id, "005930", "Samsung Electronics", sort_order=1)
    users.add_watchlist(alice_id, "000660", "SK hynix", sort_order=2)
    users.add_watchlist(bob_id, "035420", "NAVER", sort_order=1)
    users.set_setting(alice_id, "chart_timeframes", ["1m", "3m", "5m"])
    users.set_setting(bob_id, "alert_thresholds", {"EVENT_VOLUME_RATIO": 1.6})
    users.add_alert_rule(alice_id, "VOLUME_SPIKE", {"EVENT_VOLUME_RATIO": 1.8}, ["console"])
    users.add_alert_rule(bob_id, "NEAR_BOX_HIGH", {"EVENT_BOX_HIGH_POSITION": 0.85}, ["console"])
    return users


def create_app_context(db_path=None):
    conn = init_db(db_path)
    users = bootstrap_demo_data(conn)
    return {"conn": conn, "users": users, "audit": AuditStore(conn)}


def run_mock_analysis(db_path=None, use_gpt=False):
    context = create_app_context(db_path)
    return run_once(context["conn"], context["users"], use_gpt=use_gpt)
