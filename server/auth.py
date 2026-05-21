"""Small FastAPI auth helpers for private beta administration."""

from app.config import ADMIN_API_TOKEN


def require_admin_token(header_value, http_exception_cls):
    if not ADMIN_API_TOKEN:
        return True
    if header_value != ADMIN_API_TOKEN:
        raise http_exception_cls(status_code=401, detail="invalid admin token")
    return True
