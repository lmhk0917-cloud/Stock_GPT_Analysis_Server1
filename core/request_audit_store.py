"""Server request and usage audit storage."""

import re

from core.database import dumps_json, row_to_dict, utc_now


USER_ID_PATTERN = re.compile(r"/users/(\d+)(?:/|$)")


class RequestAuditStore:
    def __init__(self, conn):
        self.conn = conn

    def log_request(self, method, path, status_code=None, duration_ms=None, request_summary=None, user_id=None):
        if user_id is None:
            user_id = self._extract_user_id(path)
        self.conn.execute(
            """
            INSERT INTO api_request_logs(
              user_id, method, path, status_code, duration_ms, request_summary_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                method,
                path,
                status_code,
                duration_ms,
                dumps_json(request_summary or {}),
                utc_now(),
            ),
        )
        self.conn.commit()

    def list_logs(self, limit=100, user_id=None):
        if user_id is None:
            rows = self.conn.execute(
                "SELECT * FROM api_request_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            )
        else:
            rows = self.conn.execute(
                "SELECT * FROM api_request_logs WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            )
        return [row_to_dict(row) for row in rows]

    def _extract_user_id(self, path):
        match = USER_ID_PATTERN.search(path or "")
        return int(match.group(1)) if match else None
