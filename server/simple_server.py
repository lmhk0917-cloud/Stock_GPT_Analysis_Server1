"""Dependency-free development HTTP server.

FastAPI remains the intended production API layer. This module exists so the
server can be exercised in the current Python environment before dependencies
are installed.
"""

import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from app.config import ADMIN_API_TOKEN
from broker.order_service import OrderService
from core.audit_store import AuditStore
from core.database import init_db
from core.memory_store import UserMemoryStore
from core.request_audit_store import RequestAuditStore
from core.user_store import UserStore
from market_data.realtime_worker import run_once
from server.chat_service import ChatService


USER_CHAT_RE = re.compile(r"^/users/(\d+)/chat$")
USER_MEMORY_RE = re.compile(r"^/users/(\d+)/memory$")


class ServerState:
    def __init__(self, db_path=None):
        self.conn = init_db(db_path)
        self.users = UserStore(self.conn)
        self.audit = AuditStore(self.conn)
        self.memory = UserMemoryStore(self.conn)
        self.request_audit = RequestAuditStore(self.conn)


def make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        server_version = "StockGPTSimpleServer/0.1"

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def _dispatch(self, method):
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                if method == "GET" and path == "/health":
                    self._send(200, {"status": "ok", "server": "simple"})
                elif method == "GET" and path == "/users":
                    self._send(200, state.users.list_users())
                elif method == "POST" and path == "/users":
                    payload = self._read_json()
                    user_id = state.users.upsert_user(
                        payload["login_id"],
                        payload["display_name"],
                        role=payload.get("role", "user"),
                        telegram_chat_id=payload.get("telegram_chat_id"),
                    )
                    self._send(200, state.users.get_user(user_id))
                elif method == "GET" and USER_MEMORY_RE.match(path):
                    user_id = int(USER_MEMORY_RE.match(path).group(1))
                    self._send(200, state.memory.list_memory(user_id))
                elif method == "POST" and USER_CHAT_RE.match(path):
                    user_id = int(USER_CHAT_RE.match(path).group(1))
                    payload = self._read_json()
                    result = ChatService(state.conn).ask(
                        user_id,
                        payload["content"],
                        session_id=payload.get("session_id"),
                        title=payload.get("title"),
                    )
                    self._send(200, result)
                elif method == "GET" and path == "/admin/overview":
                    self._require_admin()
                    self._send(200, self._overview())
                elif method == "POST" and path == "/admin/run-analysis":
                    self._require_admin()
                    self._send(200, run_once(state.conn, state.users))
                elif method == "GET" and path == "/admin/request-logs":
                    self._require_admin()
                    query = parse_qs(parsed.query)
                    limit = int(query.get("limit", ["100"])[0])
                    self._send(200, state.request_audit.list_logs(limit=limit))
                else:
                    self._send(404, {"detail": "not found"})
            except PermissionError as exc:
                self._send(401, {"detail": str(exc)})
            except Exception as exc:
                self._send(500, {"detail": str(exc)})
            finally:
                state.request_audit.log_request(method, path, status_code=200, request_summary={"simple_server": True})

        def _overview(self):
            counts = {}
            for table in (
                "users",
                "user_watchlists",
                "analysis_results",
                "event_logs",
                "notification_logs",
                "broker_credentials",
                "order_requests",
                "api_request_logs",
                "gpt_call_logs",
            ):
                counts[table] = state.conn.execute("SELECT COUNT(*) FROM {}".format(table)).fetchone()[0]
            return {"status": "ok", "counts": counts, "usage": state.audit.usage_summary()}

        def _read_json(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))

        def _require_admin(self):
            if ADMIN_API_TOKEN and self.headers.get("X-Admin-Token") != ADMIN_API_TOKEN:
                raise PermissionError("invalid admin token")

        def _send(self, status, payload):
            raw = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, fmt, *args):
            return

    return Handler


def run(host="127.0.0.1", port=8765, db_path=None):
    state = ServerState(db_path=db_path)
    httpd = HTTPServer((host, port), make_handler(state))
    print("Serving on http://{}:{}".format(host, port))
    httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db-path", default=None)
    args = parser.parse_args()
    run(args.host, args.port, db_path=args.db_path)


if __name__ == "__main__":
    main()
