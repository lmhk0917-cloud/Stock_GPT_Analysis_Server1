"""Small FastAPI auth helpers for private beta administration."""

from app.config import ADMIN_API_TOKEN


def require_admin_token(header_value, http_exception_cls):
    if not ADMIN_API_TOKEN:
        return True
    if header_value != ADMIN_API_TOKEN:
        raise http_exception_cls(status_code=401, detail="invalid admin token")
    return True


def require_user_token(session_store, user_id, token, admin_token, http_exception_cls):
    if ADMIN_API_TOKEN and admin_token == ADMIN_API_TOKEN:
        return True
    user = session_store.get_user_for_token(token)
    if not user:
        raise http_exception_cls(status_code=401, detail="invalid user token")
    if int(user["id"]) != int(user_id):
        raise http_exception_cls(status_code=403, detail="token does not match user")
    return True
