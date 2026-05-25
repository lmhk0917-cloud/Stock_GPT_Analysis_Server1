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
    }

    for name, ok in checks.items():
        print("{}={}".format(name, "OK" if ok else "FAIL"))
    if not all(checks.values()):
        raise SystemExit(1)
    print("ADMIN_UI_SMOKE_TEST_OK")


if __name__ == "__main__":
    main()
