"""Smoke test for the FastAPI app using TestClient."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("CREDENTIAL_MASTER_KEY", "local-fastapi-smoke-test-master-key")
os.environ["OPENAI_API_KEY"] = ""

from app.config import ADMIN_API_TOKEN
from fastapi.testclient import TestClient
from server.api import app


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
        "overview": overview.status_code == 200 and overview.json()["status"] == "ok",
    }
    for name, ok in checks.items():
        print("{}={}".format(name, "OK" if ok else "FAIL"))
    if not all(checks.values()):
        raise SystemExit(1)
    print("FASTAPI_SMOKE_TEST_OK")


if __name__ == "__main__":
    main()
