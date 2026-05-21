"""Smoke test for the dependency-free HTTP server."""

import json
import os
import sys
import tempfile
import threading
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("CREDENTIAL_MASTER_KEY", "local-server-smoke-test-master-key")

from server.simple_server import ServerState, make_handler
from http.server import HTTPServer


def request(method, url, payload=None):
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    temp_dir = tempfile.mkdtemp(prefix="stock_server_http_")
    db_path = os.path.join(temp_dir, "server_smoke.db")
    state = ServerState(db_path=db_path)
    httpd = HTTPServer(("127.0.0.1", 0), make_handler(state))
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()
    time.sleep(0.1)

    base = "http://127.0.0.1:{}".format(port)
    health = request("GET", base + "/health")
    user = request("POST", base + "/users", {"login_id": "smoke", "display_name": "Smoke User"})
    chat = request("POST", base + "/users/{}/chat".format(user["id"]), {"content": "서버 상태 확인"})
    overview = request("GET", base + "/admin/overview")

    httpd.shutdown()
    thread.join(timeout=5)

    checks = {
        "health": health["status"] == "ok",
        "user": user["login_id"] == "smoke",
        "chat": bool(chat["answer"]),
        "overview": overview["status"] == "ok",
    }
    for name, ok in checks.items():
        print("{}={}".format(name, "OK" if ok else "FAIL"))
    if not all(checks.values()):
        raise SystemExit(1)
    print("SERVER_SMOKE_TEST_OK db_path={}".format(db_path))


if __name__ == "__main__":
    main()
