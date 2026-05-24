"""Offline stability check for the multiuser server MVP."""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("CREDENTIAL_MASTER_KEY", "local-stability-check-master-key")
os.environ["OPENAI_API_KEY"] = ""

from broker.order_service import OrderService
from core.credential_store import BrokerCredentialStore
from core.database import init_db
from core.memory_store import UserMemoryStore
from core.request_audit_store import RequestAuditStore
from core.session_store import SessionStore
from core.user_store import UserStore
from server.chat_service import ChatService
from server.services import bootstrap_demo_data
from market_data.realtime_worker import run_once
from market_data.adapters.factory import create_market_data_adapter


def main():
    temp_dir = tempfile.mkdtemp(prefix="stock_server_mvp_")
    db_path = os.path.join(temp_dir, "stability_check.db")
    conn = init_db(db_path)
    users = bootstrap_demo_data(conn)
    alice_id = users.get_user_by_login("alice")["id"]
    session = SessionStore(conn).create_session(alice_id, label="stability")
    session_user = SessionStore(conn).get_user_for_token(session["token"])
    credentials = BrokerCredentialStore(conn)
    credentials.upsert_credentials(
        alice_id,
        "kis_rest",
        "demo-app-key",
        "demo-app-secret",
        account_no="12345678-01",
        can_read=True,
        can_order=False,
    )
    decrypted = credentials.get_decrypted_credentials(alice_id, "kis_rest")
    memory = UserMemoryStore(conn)
    memory.add_memory(alice_id, {"risk_style": "short-term test profile"}, memory_type="preference")
    session_id = memory.create_chat_session(alice_id, "stability chat")
    memory.add_chat_message(session_id, "user", "005930 상태 요약해줘", token_count=12)
    RequestAuditStore(conn).log_request("POST", "/users/{}/chat-sessions".format(alice_id), 200, 2.5)
    chat_result = ChatService(conn).ask(alice_id, "내 관심종목 최근 이벤트를 요약해줘", session_id=session_id)
    order = OrderService(conn).request_order(
        alice_id,
        "kis_rest",
        "KRX",
        "005930",
        "buy",
        1,
        approval_text="주문 위험을 확인했고 실행을 승인합니다",
    )
    adapter = create_market_data_adapter("mock")
    quote = adapter.get_quote("KRX", "005930")
    results = run_once(conn, users, use_gpt=False)

    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    watch_count = conn.execute("SELECT COUNT(*) FROM user_watchlists").fetchone()[0]
    result_count = conn.execute("SELECT COUNT(*) FROM analysis_results").fetchone()[0]
    event_count = conn.execute("SELECT COUNT(*) FROM event_logs").fetchone()[0]
    notification_count = conn.execute("SELECT COUNT(*) FROM notification_logs").fetchone()[0]
    credential_count = conn.execute("SELECT COUNT(*) FROM broker_credentials").fetchone()[0]
    order_count = conn.execute("SELECT COUNT(*) FROM order_requests").fetchone()[0]
    memory_count = conn.execute("SELECT COUNT(*) FROM user_memory").fetchone()[0]
    chat_count = conn.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0]
    request_log_count = conn.execute("SELECT COUNT(*) FROM api_request_logs").fetchone()[0]
    gpt_log_count = conn.execute("SELECT COUNT(*) FROM gpt_call_logs").fetchone()[0]
    session_count = conn.execute("SELECT COUNT(*) FROM user_sessions").fetchone()[0]

    checks = {
        "users": user_count >= 2,
        "user_sessions": session_count == 1 and session_user["id"] == alice_id,
        "watchlists": watch_count >= 3,
        "broker_credentials": credential_count == 1 and decrypted["app_secret"] == "demo-app-secret",
        "order_disabled_gate": order_count == 1 and order["status"] == "blocked_order_api_disabled",
        "user_memory": memory_count == 1 and chat_count >= 3 and chat_result["answer"],
        "request_audit": request_log_count == 1,
        "chat_gateway": gpt_log_count >= 1,
        "adapter_factory": quote["provider"] == "mock",
        "analysis_results": result_count == len(results),
        "events": event_count > 0,
        "notifications": notification_count > 0,
    }

    for name, ok in checks.items():
        print("{}={}".format(name, "OK" if ok else "FAIL"))

    if not all(checks.values()):
        raise SystemExit(1)

    print("STABILITY_CHECK_OK db_path={}".format(db_path))


if __name__ == "__main__":
    main()
