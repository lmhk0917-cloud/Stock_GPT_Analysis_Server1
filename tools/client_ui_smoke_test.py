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

    providers = client.get("/broker-providers")
    provider_ids = [item["id"] for item in providers.json()] if providers.status_code == 200 else []
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
    credential = client.put(
        "/users/{}/broker-credentials".format(user_id),
        headers=user_headers,
        json={
            "provider": "kis_rest",
            "environment": "paper",
            "app_key": "client-ui-smoke-app-key",
            "app_secret": "client-ui-smoke-app-secret",
            "account_no": "00000000",
            "can_read": True,
            "can_order": False,
        },
    )
    invalid_credential = client.put(
        "/users/{}/broker-credentials".format(user_id),
        headers=user_headers,
        json={
            "provider": "kis_rest",
            "environment": "unsupported",
            "app_key": "bad",
            "app_secret": "bad",
        },
    )
    kiwoom_alias_credential = client.put(
        "/users/{}/broker-credentials".format(user_id),
        headers=user_headers,
        json={
            "provider": "kiwoom",
            "environment": "live",
            "app_key": "kiwoom-app-key",
            "app_secret": "kiwoom-app-secret",
            "account_no": "00000000",
            "can_read": True,
            "can_order": False,
        },
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
        "broker_providers": providers.status_code == 200
        and {"mock", "kis_rest", "kiwoom_legacy"}.issubset(set(provider_ids)),
        "user": user.status_code == 200 and bool(user_id),
        "issue_user_token": issued.status_code == 200 and bool(token),
        "profile_empty": profile_empty.status_code == 200,
        "watchlist": watch.status_code == 200 and len(watch.json()) >= 1,
        "memory": memory.status_code == 200 and len(memory.json()) >= 1,
        "broker_credentials": credential.status_code == 200
        and len(credential.json()) >= 1
        and "app_key" not in credential.text
        and "client-ui-smoke-app-key" not in credential.text,
        "invalid_broker_environment": invalid_credential.status_code == 400,
        "kiwoom_alias_credential": kiwoom_alias_credential.status_code == 200
        and any(row["provider"] == "kiwoom_legacy" for row in kiwoom_alias_credential.json()),
        "chat": chat.status_code == 200 and bool(chat.json().get("answer")),
        "profile": profile.status_code == 200
        and len(profile_json.get("watchlist", [])) >= 1
        and len(profile_json.get("memory", [])) >= 1
        and len(profile_json.get("broker_credentials", [])) >= 1
        and "client-ui-smoke-app-secret" not in profile.text,
        "unauthorized": unauthorized.status_code == 401,
    }

    for name, ok in checks.items():
        print("{}={}".format(name, "OK" if ok else "FAIL"))
    if not all(checks.values()):
        raise SystemExit(1)
    print("CLIENT_UI_SMOKE_TEST_OK")


if __name__ == "__main__":
    main()
