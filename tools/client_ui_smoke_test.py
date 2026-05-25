"""Smoke test for the private-beta user client UI and token-protected APIs."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("CREDENTIAL_MASTER_KEY", "local-client-ui-smoke-test-master-key")
os.environ["OPENAI_API_KEY"] = ""

from app.config import ADMIN_API_TOKEN
from fastapi.testclient import TestClient
from server.api import app


def main():
    client = TestClient(app)
    admin_headers = {"X-Admin-Token": ADMIN_API_TOKEN} if ADMIN_API_TOKEN else {}

    page = client.get("/client/ui")
    user = client.post(
        "/users",
        headers=admin_headers,
        json={"login_id": "client_ui_smoke", "display_name": "Client UI Smoke"},
    )
    user_id = user.json().get("id") if user.status_code == 200 else None
    issued = client.post(
        "/admin/users/{}/sessions".format(user_id),
        headers=admin_headers,
        json={"label": "client-ui-smoke"},
    )
    token = issued.json().get("token") if issued.status_code == 200 else ""
    user_headers = {"X-User-Token": token}

    profile_empty = client.get("/users/{}/profile".format(user_id), headers=user_headers)
    watch = client.post(
        "/users/{}/watchlist".format(user_id),
        headers=user_headers,
        json={"market": "KRX", "code": "005930", "name": "Samsung Electronics"},
    )
    memory = client.post(
        "/users/{}/memory".format(user_id),
        headers=user_headers,
        json={"memory_type": "preference", "content": {"text": "Prefer liquid large caps"}},
    )
    chat = client.post(
        "/users/{}/chat".format(user_id),
        headers=user_headers,
        json={"content": "관심종목과 개인 메모리를 한 문장으로 요약해줘"},
    )
    profile = client.get("/users/{}/profile".format(user_id), headers=user_headers)
    unauthorized = client.get("/users/{}/profile".format(user_id))

    profile_json = profile.json() if profile.status_code == 200 else {}
    checks = {
        "client_ui": page.status_code == 200 and "Stock_GPT_Analysis_Server1" in page.text,
        "user": user.status_code == 200 and bool(user_id),
        "issue_user_token": issued.status_code == 200 and bool(token),
        "profile_empty": profile_empty.status_code == 200,
        "watchlist": watch.status_code == 200 and len(watch.json()) >= 1,
        "memory": memory.status_code == 200 and len(memory.json()) >= 1,
        "chat": chat.status_code == 200 and bool(chat.json().get("answer")),
        "profile": profile.status_code == 200
        and len(profile_json.get("watchlist", [])) >= 1
        and len(profile_json.get("memory", [])) >= 1,
        "unauthorized": unauthorized.status_code == 401,
    }

    for name, ok in checks.items():
        print("{}={}".format(name, "OK" if ok else "FAIL"))
    if not all(checks.values()):
        raise SystemExit(1)
    print("CLIENT_UI_SMOKE_TEST_OK")


if __name__ == "__main__":
    main()
