"""FastAPI endpoints for the private multiuser analysis MVP."""

import time
from pathlib import Path

from broker.order_service import OrderService
from server.auth import require_admin_token, require_user_token
from server.chat_service import ChatService
from core.database import init_db
from core.user_store import UserStore
from core.audit_store import AuditStore
from core.credential_store import BrokerCredentialStore
from core.memory_store import UserMemoryStore
from core.request_audit_store import RequestAuditStore
from core.session_store import SessionStore
from market_data.realtime_worker import run_once


conn = init_db()
users = UserStore(conn)
audit = AuditStore(conn)
memory = UserMemoryStore(conn)
request_audit = RequestAuditStore(conn)
sessions = SessionStore(conn)

try:
    from fastapi import FastAPI, Header, HTTPException
    from fastapi.responses import HTMLResponse
    from pydantic import BaseModel
except Exception:
    FastAPI = None
    Header = None
    HTTPException = Exception
    HTMLResponse = None
    BaseModel = object


if BaseModel is object:
    class UserCreate(object):
        pass

    class LoginCreate(object):
        pass

    class WatchCreate(object):
        pass

    class SettingPut(object):
        pass

    class BrokerCredentialPut(object):
        pass

    class OrderRequestCreate(object):
        pass

    class MemoryCreate(object):
        pass

    class ChatSessionCreate(object):
        pass

    class ChatMessageCreate(object):
        pass

    class ChatAskCreate(object):
        pass
else:
    class UserCreate(BaseModel):
        login_id: str
        display_name: str
        role: str = "user"
        telegram_chat_id: str = None

    class LoginCreate(BaseModel):
        login_id: str
        label: str = "default"

    class WatchCreate(BaseModel):
        market: str = "KRX"
        code: str
        name: str
        enabled: bool = True
        sort_order: int = 0

    class SettingPut(BaseModel):
        value: object

    class BrokerCredentialPut(BaseModel):
        provider: str = "kis_rest"
        environment: str = "paper"
        app_key: str
        app_secret: str
        account_no: str = None
        can_read: bool = True
        can_order: bool = False

    class OrderRequestCreate(BaseModel):
        provider: str = "kis_rest"
        market: str = "KRX"
        code: str
        side: str
        quantity: float
        order_type: str = "market"
        limit_price: float = None
        approval_text: str = None

    class MemoryCreate(BaseModel):
        content: object
        memory_type: str = "preference"
        visibility: str = "private"

    class ChatSessionCreate(BaseModel):
        title: str = "New chat"

    class ChatMessageCreate(BaseModel):
        role: str
        content: str
        token_count: int = None

    class ChatAskCreate(BaseModel):
        content: str
        session_id: int = None
        title: str = None


def create_api():
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Install fastapi and uvicorn to run the HTTP server.")

    app = FastAPI(title="Stock_GPT_Analysis_Server1")

    @app.middleware("http")
    async def audit_requests(request, call_next):
        started = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - started) * 1000, 3)
        request_audit.log_request(
            request.method,
            request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            request_summary={
                "query": dict(request.query_params),
                "client": request.client.host if request.client else None,
            },
        )
        return response

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/admin/ui", response_class=HTMLResponse)
    def admin_ui():
        path = Path(__file__).resolve().parent / "static" / "admin.html"
        return HTMLResponse(path.read_text(encoding="utf-8"))

    @app.post("/auth/login")
    def login(payload: LoginCreate):
        user = users.get_user_by_login(payload.login_id)
        if not user:
            raise HTTPException(status_code=404, detail="user not found")
        session = sessions.create_session(user["id"], label=payload.label)
        return {
            "user": user,
            "token": session["token"],
            "session_id": session["id"],
            "expires_at": session["expires_at"],
        }

    @app.get("/users")
    def list_users(x_admin_token: str = Header(None)):
        _require_admin(x_admin_token)
        return users.list_users()

    @app.post("/users")
    def create_user(payload: UserCreate, x_admin_token: str = Header(None)):
        _require_admin(x_admin_token)
        user_id = users.upsert_user(
            payload.login_id,
            payload.display_name,
            role=payload.role,
            telegram_chat_id=payload.telegram_chat_id,
        )
        return users.get_user(user_id)

    @app.get("/users/{user_id}/watchlist")
    def list_watchlist(user_id: int, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        return users.list_watchlist(user_id)

    @app.post("/users/{user_id}/watchlist")
    def add_watchlist(user_id: int, payload: WatchCreate, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        users.add_watchlist(user_id, payload.code, payload.name, payload.market, payload.enabled, payload.sort_order)
        return users.list_watchlist(user_id)

    @app.delete("/users/{user_id}/watchlist/{watch_id}")
    def remove_watchlist(user_id: int, watch_id: int, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        users.remove_watchlist(user_id, watch_id)
        return {"deleted": True}

    @app.get("/users/{user_id}/settings")
    def get_settings(user_id: int, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        return users.get_settings(user_id)

    @app.put("/users/{user_id}/settings/{key}")
    def set_setting(user_id: int, key: str, payload: SettingPut, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        users.set_setting(user_id, key, payload.value)
        return users.get_settings(user_id)

    @app.get("/users/{user_id}/memory")
    def list_memory(user_id: int, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        return memory.list_memory(user_id)

    @app.post("/users/{user_id}/memory")
    def add_memory(user_id: int, payload: MemoryCreate, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        memory.add_memory(user_id, payload.content, payload.memory_type, payload.visibility)
        return memory.list_memory(user_id)

    @app.post("/users/{user_id}/chat-sessions")
    def create_chat_session(user_id: int, payload: ChatSessionCreate, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        session_id = memory.create_chat_session(user_id, payload.title)
        return {"id": session_id, "user_id": user_id, "title": payload.title}

    @app.get("/users/{user_id}/sessions")
    def list_user_sessions(user_id: int, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        return sessions.list_sessions(user_id)

    @app.delete("/users/{user_id}/sessions/{session_id}")
    def revoke_user_session(user_id: int, session_id: int, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        sessions.revoke_session(user_id, session_id)
        return {"revoked": True}

    @app.get("/chat-sessions/{session_id}/messages")
    def list_chat_messages(session_id: int, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        user_id = _chat_session_user_id(session_id)
        _require_user_access(user_id, x_user_token, x_admin_token)
        return memory.list_chat_messages(session_id)

    @app.post("/chat-sessions/{session_id}/messages")
    def add_chat_message(session_id: int, payload: ChatMessageCreate, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        user_id = _chat_session_user_id(session_id)
        _require_user_access(user_id, x_user_token, x_admin_token)
        message_id = memory.add_chat_message(session_id, payload.role, payload.content, payload.token_count)
        return {"id": message_id}

    @app.post("/users/{user_id}/chat")
    def ask_chat(user_id: int, payload: ChatAskCreate, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        return ChatService(conn).ask(
            user_id,
            payload.content,
            session_id=payload.session_id,
            title=payload.title,
        )

    @app.get("/users/{user_id}/broker-credentials")
    def list_broker_credentials(user_id: int, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        store = _credential_store()
        return store.list_credentials_meta(user_id)

    @app.put("/users/{user_id}/broker-credentials")
    def put_broker_credentials(user_id: int, payload: BrokerCredentialPut, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        store = _credential_store()
        store.upsert_credentials(
            user_id,
            payload.provider,
            payload.app_key,
            payload.app_secret,
            account_no=payload.account_no,
            environment=payload.environment,
            can_read=payload.can_read,
            can_order=payload.can_order,
        )
        return store.list_credentials_meta(user_id)

    @app.get("/users/{user_id}/orders")
    def list_orders(user_id: int, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        return OrderService(conn).list_orders(user_id)

    @app.post("/users/{user_id}/orders")
    def request_order(user_id: int, payload: OrderRequestCreate, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        return OrderService(conn).request_order(
            user_id,
            payload.provider,
            payload.market,
            payload.code,
            payload.side,
            payload.quantity,
            order_type=payload.order_type,
            limit_price=payload.limit_price,
            approval_text=payload.approval_text,
        )

    @app.get("/users/{user_id}/reports")
    def list_reports(user_id: int, x_user_token: str = Header(None), x_admin_token: str = Header(None)):
        _require_user_access(user_id, x_user_token, x_admin_token)
        return audit.reports_for_user(user_id)

    @app.get("/symbols/{market}/{code}/chart")
    def get_chart(market: str, code: str):
        rows = conn.execute(
            """
            SELECT * FROM market_prices
            WHERE market = ? AND code = ?
            ORDER BY timestamp DESC
            LIMIT 120
            """,
            (market, code),
        ).fetchall()
        return [dict(row) for row in rows]

    @app.get("/admin/overview")
    def admin_overview(x_admin_token: str = Header(None)):
        _require_admin(x_admin_token)
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
            counts[table] = conn.execute("SELECT COUNT(*) FROM {}".format(table)).fetchone()[0]
        return {
            "status": "ok",
            "counts": counts,
            "usage": audit.usage_summary(),
        }

    @app.post("/admin/run-analysis")
    def admin_run_analysis(x_admin_token: str = Header(None)):
        _require_admin(x_admin_token)
        return run_once(conn, users)

    @app.post("/admin/run-backfill")
    def admin_run_backfill(x_admin_token: str = Header(None)):
        _require_admin(x_admin_token)
        return run_once(conn, users)

    @app.get("/admin/request-logs")
    def admin_request_logs(limit: int = 100, user_id: int = None, x_admin_token: str = Header(None)):
        _require_admin(x_admin_token)
        return request_audit.list_logs(limit=limit, user_id=user_id)

    @app.get("/admin/gpt-logs")
    def admin_gpt_logs(limit: int = 100, x_admin_token: str = Header(None)):
        _require_admin(x_admin_token)
        return _query_rows(
            """
            SELECT id, started_at, finished_at, status, requested_count, symbols_json, model,
                   prompt_tokens, completion_tokens, total_tokens, result_preview
            FROM gpt_call_logs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )

    @app.get("/admin/orders")
    def admin_orders(limit: int = 100, user_id: int = None, x_admin_token: str = Header(None)):
        _require_admin(x_admin_token)
        if user_id is None:
            return _query_rows(
                """
                SELECT id, user_id, provider, market, code, side, quantity, order_type,
                       limit_price, status, approval_required, created_at, updated_at
                FROM order_requests
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )
        return _query_rows(
            """
            SELECT id, user_id, provider, market, code, side, quantity, order_type,
                   limit_price, status, approval_required, created_at, updated_at
            FROM order_requests
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        )

    @app.get("/admin/users/{user_id}/details")
    def admin_user_details(user_id: int, x_admin_token: str = Header(None)):
        _require_admin(x_admin_token)
        user = _require_user(user_id)
        return {
            "user": user,
            "usage": audit.usage_summary(user_id),
            "watchlist": users.list_watchlist(user_id),
            "settings": users.get_settings(user_id),
            "memory": memory.list_memory(user_id),
            "sessions": sessions.list_sessions(user_id),
            "broker_credentials": _safe_credential_meta(user_id),
            "orders": OrderService(conn).list_orders(user_id),
            "reports": audit.reports_for_user(user_id),
        }

    return app


def _query_rows(sql, params=()):
    return [dict(row) for row in conn.execute(sql, params).fetchall()]


def _safe_credential_meta(user_id):
    try:
        return _credential_store().list_credentials_meta(user_id)
    except HTTPException as exc:
        return {"error": exc.detail}


def _require_user(user_id):
    user = users.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return user


def _require_user_access(user_id, user_token, admin_token):
    _require_user(user_id)
    return require_user_token(sessions, user_id, user_token, admin_token, HTTPException)


def _chat_session_user_id(session_id):
    row = conn.execute("SELECT user_id FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="chat session not found")
    return row["user_id"]


def _credential_store():
    try:
        return BrokerCredentialStore(conn)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _require_admin(token):
    return require_admin_token(token, HTTPException)


app = create_api() if FastAPI is not None else None
