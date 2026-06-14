"""Smoke test for the FastAPI app using TestClient."""

import os
import sys
import uuid
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("CREDENTIAL_MASTER_KEY", "local-fastapi-smoke-test-master-key")
os.environ["OPENAI_API_KEY"] = ""

from app.config import ADMIN_API_TOKEN
from fastapi.testclient import TestClient
from server.api import app, conn


def main():
    client = TestClient(app)
    admin_headers = {"X-Admin-Token": ADMIN_API_TOKEN} if ADMIN_API_TOKEN else {}
    health = client.get("/health")
    user = client.post(
        "/users",
        headers=admin_headers,
        json={"login_id": "fastapi_smoke", "display_name": "FastAPI Smoke"},
    )
    login = client.post("/auth/login", json={"login_id": "fastapi_smoke", "label": "smoke"})
    token = login.json()["token"] if login.status_code == 200 else ""
    unauthorized = client.post(
        "/users/{}/chat".format(user.json().get("id")),
        json={"content": "권한 없는 요청"},
    )
    chat = client.post(
        "/users/{}/chat".format(user.json().get("id")),
        headers={"X-User-Token": token},
        json={"content": "FastAPI 인증 smoke test"},
    )
    symbol_search = client.get("/symbols/search", params={"q": "삼성", "market": "KRX"})
    user_analysis = client.post(
        "/users/{}/analysis/run".format(user.json().get("id")),
        headers={"X-User-Token": token},
        json={"market": "KRX", "code": "005930", "name": "삼성전자", "use_gpt": False},
    )
    seed_tick_evidence("005930")
    evidence = client.get("/users/{}/evidence".format(user.json().get("id")), headers={"X-User-Token": token})
    evidence_json = evidence.json() if evidence.status_code == 200 else {}
    profile = client.get("/users/{}/profile".format(user.json().get("id")), headers={"X-User-Token": token})
    overview = client.get("/admin/overview", headers=admin_headers)

    checks = {
        "health": health.status_code == 200 and health.json()["status"] == "ok",
        "user": user.status_code == 200,
        "login": login.status_code == 200 and bool(token),
        "unauthorized_user_chat": unauthorized.status_code == 401,
        "authorized_user_chat": chat.status_code == 200 and bool(chat.json().get("answer")),
        "symbol_search": symbol_search.status_code == 200
        and any(row["code"] == "005930" for row in symbol_search.json()),
        "user_analysis": user_analysis.status_code == 200
        and len(user_analysis.json().get("results", [])) == 1,
        "tick_evidence": evidence.status_code == 200
        and evidence_json.get("symbols", [{}])[0].get("tick_evidence", {}).get("sample_size", 0) >= 3
        and evidence_json.get("symbols", [{}])[0].get("tick_evidence", {}).get("sample_vwap") is not None
        and "fx_context" in evidence_json
        and "paper_trade_feedback" in evidence_json.get("symbols", [{}])[0],
        "profile_evidence": profile.status_code == 200
        and "evidence_pack" in profile.json(),
        "overview": overview.status_code == 200 and overview.json()["status"] == "ok",
        "usage_cost_fields": overview.status_code == 200
        and "estimated_gpt_cost_usd" in overview.json().get("usage", {}),
    }
    for name, ok in checks.items():
        print("{}={}".format(name, "OK" if ok else "FAIL"))
    if not all(checks.values()):
        raise SystemExit(1)
    print("FASTAPI_SMOKE_TEST_OK")


def seed_tick_evidence(code):
    now = datetime.now()
    base_id = uuid.uuid4().hex
    rows = [
        (base_id + "-1", code, "145501", 70000, 100, 102.5, now - timedelta(seconds=20)),
        (base_id + "-2", code, "145502", 70100, 120, 103.0, now - timedelta(seconds=10)),
        (base_id + "-3", code, "145503", 70200, 130, 104.0, now),
    ]
    for source_event_id, tick_code, trade_time, price, volume, strength, received_at in rows:
        conn.execute(
            """
            INSERT OR IGNORE INTO kiwoom_legacy_ticks(
              source_event_id, market, code, trade_time, price, change_rate, acc_volume,
              tick_volume, open_price, high_price, low_price, strength, received_at,
              imported_at, raw_json
            )
            VALUES (?, 'KRX', ?, ?, ?, 0.1, ?, ?, ?, ?, ?, ?, ?, ?, '{}')
            """,
            (
                source_event_id,
                tick_code,
                trade_time,
                price,
                volume,
                volume,
                price - 50,
                price + 50,
                price - 100,
                strength,
                received_at.strftime("%Y-%m-%d %H:%M:%S.%f"),
                now.strftime("%Y-%m-%d %H:%M:%S.%f"),
            ),
        )
    conn.commit()


if __name__ == "__main__":
    main()
