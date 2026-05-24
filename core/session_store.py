"""User session token storage."""

import hashlib
import secrets

from core.database import row_to_dict, utc_now


class SessionStore:
    def __init__(self, conn):
        self.conn = conn

    def create_session(self, user_id, label=None, expires_at=None):
        token = secrets.token_urlsafe(32)
        token_hash = self.hash_token(token)
        now = utc_now()
        cur = self.conn.execute(
            """
            INSERT INTO user_sessions(user_id, token_hash, label, expires_at, created_at, last_used_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, token_hash, label, expires_at, now, now),
        )
        self.conn.commit()
        return {
            "id": cur.lastrowid,
            "user_id": user_id,
            "token": token,
            "label": label,
            "expires_at": expires_at,
            "created_at": now,
        }

    def get_user_for_token(self, token):
        if not token:
            return None
        token_hash = self.hash_token(token)
        row = self.conn.execute(
            """
            SELECT u.*
            FROM user_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
              AND s.revoked_at IS NULL
              AND u.is_active = 1
              AND (s.expires_at IS NULL OR s.expires_at > ?)
            """,
            (token_hash, utc_now()),
        ).fetchone()
        if not row:
            return None
        self.conn.execute(
            "UPDATE user_sessions SET last_used_at = ? WHERE token_hash = ?",
            (utc_now(), token_hash),
        )
        self.conn.commit()
        return row_to_dict(row)

    def list_sessions(self, user_id):
        rows = self.conn.execute(
            """
            SELECT id, user_id, label, expires_at, revoked_at, created_at, last_used_at
            FROM user_sessions
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        )
        return [row_to_dict(row) for row in rows]

    def revoke_session(self, user_id, session_id):
        self.conn.execute(
            """
            UPDATE user_sessions
            SET revoked_at = ?
            WHERE user_id = ? AND id = ? AND revoked_at IS NULL
            """,
            (utc_now(), user_id, session_id),
        )
        self.conn.commit()

    def hash_token(self, token):
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
