"""Smoke test for the FastAPI admin dashboard and admin-only views."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("CREDENTIAL_MASTER_KEY", "local-admin-ui-smoke-test-master-key")
os.environ["OPENAI_API_KEY"] = ""

from app.config import ADMIN_API_TOKEN
from fastapi.testclient import TestClient
from server.api import app


def main():
    client = TestClient(app)
    admin_headers = {"X-Admin-Token": ADMIN_API_TOKEN} if ADMIN_API_TOKEN else {}

    page = client.get("/admin/ui")
    user = client.post(
        "/users",
        headers=admin_headers,
        json={"login_id": "admin_ui_smoke", "display_name": "Admin UI Smoke"},
    )
    user_id = user.json().get("id") if user.status_code == 200 else None
    overview = client.get("/admin/overview", headers=admin_headers)
    requests = client.get("/admin/request-logs?limit=10", headers=admin_headers)
    gpt = client.get("/admin/gpt-logs?limit=10", headers=admin_headers)
    orders = client.get("/admin/orders?limit=10", headers=admin_headers)
    detail = client.get("/admin/users/{}/details".format(user_id), headers=admin_headers)
    issued = client.post(
        "/admin/users/{}/sessions".format(user_id),
        headers=admin_headers,
        json={"label": "admin-ui-smoke"},
    )
    token = issued.json().get("token") if issued.status_code == 200 else ""
    user_chat = client.post(
        "/users/{}/chat".format(user_id),
        headers={"X-User-Token": token},
        json={"content": "관리자 발급 토큰 smoke test"},
    )
    revoked_one = client.delete(
        "/admin/users/{}/sessions/{}".format(user_id, issued.json().get("session_id")),
        headers=admin_headers,
    )
    revoked_token_chat = client.post(
        "/users/{}/chat".format(user_id),
        headers={"X-User-Token": token},
        json={"content": "폐기된 토큰 smoke test"},
    )
    issued_second = client.post(
        "/admin/users/{}/sessions".format(user_id),
        headers=admin_headers,
        json={"label": "admin-ui-smoke-second"},
    )
    second_token = issued_second.json().get("token") if issued_second.status_code == 200 else ""
    deactivated = client.put(
        "/admin/users/{}/status".format(user_id),
        headers=admin_headers,
        json={"is_active": False},
    )
    inactive_chat = client.post(
        "/users/{}/chat".format(user_id),
        headers={"X-User-Token": second_token},
        json={"content": "비활성 사용자 smoke test"},
    )
    reactivated = client.put(
        "/admin/users/{}/status".format(user_id),
        headers=admin_headers,
        json={"is_active": True},
    )
    issued_third = client.post(
        "/admin/users/{}/sessions".format(user_id),
        headers=admin_headers,
        json={"label": "admin-ui-smoke-third"},
    )
    revoke_all = client.post(
        "/admin/users/{}/sessions/revoke-all".format(user_id),
        headers=admin_headers,
    )

    checks = {
        "admin_ui": page.status_code == 200 and "Stock_GPT_Analysis_Server1 Admin" in page.text,
        "user": user.status_code == 200 and bool(user_id),
        "overview": overview.status_code == 200 and overview.json()["status"] == "ok",
        "request_logs": requests.status_code == 200 and isinstance(requests.json(), list),
        "gpt_logs": gpt.status_code == 200 and isinstance(gpt.json(), list),
        "orders": orders.status_code == 200 and isinstance(orders.json(), list),
        "user_detail": detail.status_code == 200 and detail.json()["user"]["id"] == user_id,
        "issue_user_token": issued.status_code == 200 and bool(token),
        "issued_token_auth": user_chat.status_code == 200 and bool(user_chat.json().get("answer")),
        "revoke_session": revoked_one.status_code == 200 and revoked_token_chat.status_code == 401,
        "deactivate_user": deactivated.status_code == 200
        and deactivated.json()["user"]["is_active"] == 0
        and inactive_chat.status_code == 401,
        "reactivate_user": reactivated.status_code == 200 and reactivated.json()["user"]["is_active"] == 1,
        "revoke_all_sessions": issued_third.status_code == 200
        and revoke_all.status_code == 200
        and all(row["revoked_at"] for row in revoke_all.json()["sessions"]),
    }

    for name, ok in checks.items():
        print("{}={}".format(name, "OK" if ok else "FAIL"))
    if not all(checks.values()):
        raise SystemExit(1)
    print("ADMIN_UI_SMOKE_TEST_OK")


if __name__ == "__main__":
    main()
