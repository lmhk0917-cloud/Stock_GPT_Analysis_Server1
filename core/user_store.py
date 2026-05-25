"""User-specific persistence for private beta accounts."""

from core.database import dumps_json, loads_json, row_to_dict, utc_now


class UserStore:
    def __init__(self, conn):
        self.conn = conn

    def create_user(self, login_id, display_name, role="user", telegram_chat_id=None):
        now = utc_now()
        cur = self.conn.execute(
            """
            INSERT INTO users(login_id, display_name, role, telegram_chat_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (login_id, display_name, role, telegram_chat_id, now, now),
        )
        self.conn.commit()
        return cur.lastrowid

    def upsert_user(self, login_id, display_name, role="user", telegram_chat_id=None):
        existing = self.get_user_by_login(login_id)
        if existing:
            now = utc_now()
            self.conn.execute(
                """
                UPDATE users
                SET display_name = ?, role = ?, telegram_chat_id = ?, updated_at = ?
                WHERE login_id = ?
                """,
                (display_name, role, telegram_chat_id, now, login_id),
            )
            self.conn.commit()
            return existing["id"]
        return self.create_user(login_id, display_name, role, telegram_chat_id)

    def list_users(self):
        return [row_to_dict(row) for row in self.conn.execute("SELECT * FROM users ORDER BY id")]

    def get_user(self, user_id):
        return row_to_dict(self.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())

    def get_user_by_login(self, login_id):
        return row_to_dict(self.conn.execute("SELECT * FROM users WHERE login_id = ?", (login_id,)).fetchone())

    def set_active(self, user_id, is_active):
        self.conn.execute(
            "UPDATE users SET is_active = ?, updated_at = ? WHERE id = ?",
            (int(bool(is_active)), utc_now(), user_id),
        )
        self.conn.commit()
        return self.get_user(user_id)

    def add_watchlist(self, user_id, code, name, market="KRX", enabled=True, sort_order=0):
        now = utc_now()
        self.conn.execute(
            """
            INSERT INTO user_watchlists(user_id, market, code, name, enabled, sort_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, market, code)
            DO UPDATE SET name = excluded.name, enabled = excluded.enabled,
              sort_order = excluded.sort_order, updated_at = excluded.updated_at
            """,
            (user_id, market, code, name, int(enabled), sort_order, now, now),
        )
        self.conn.commit()

    def remove_watchlist(self, user_id, watch_id):
        self.conn.execute("DELETE FROM user_watchlists WHERE user_id = ? AND id = ?", (user_id, watch_id))
        self.conn.commit()

    def list_watchlist(self, user_id, enabled_only=False):
        sql = "SELECT * FROM user_watchlists WHERE user_id = ?"
        params = [user_id]
        if enabled_only:
            sql += " AND enabled = 1"
        sql += " ORDER BY sort_order, id"
        return [row_to_dict(row) for row in self.conn.execute(sql, params)]

    def unique_enabled_symbols(self):
        rows = self.conn.execute(
            """
            SELECT DISTINCT market, code, name
            FROM user_watchlists
            WHERE enabled = 1
            ORDER BY market, code
            """
        )
        return [row_to_dict(row) for row in rows]

    def set_setting(self, user_id, key, value):
        now = utc_now()
        self.conn.execute(
            """
            INSERT INTO user_settings(user_id, key, value_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, key)
            DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at
            """,
            (user_id, key, dumps_json(value), now),
        )
        self.conn.commit()

    def get_settings(self, user_id):
        rows = self.conn.execute("SELECT key, value_json FROM user_settings WHERE user_id = ?", (user_id,))
        return {row["key"]: loads_json(row["value_json"]) for row in rows}

    def add_alert_rule(self, user_id, event_type, threshold=None, channels=None, market="KRX", code=None, enabled=True):
        now = utc_now()
        self.conn.execute(
            """
            INSERT INTO user_alert_rules(
              user_id, market, code, event_type, threshold_json, channels_json, enabled, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                market,
                code,
                event_type,
                dumps_json(threshold or {}),
                dumps_json(channels or ["console"]),
                int(enabled),
                now,
                now,
            ),
        )
        self.conn.commit()

    def list_alert_rules(self, user_id, enabled_only=False):
        sql = "SELECT * FROM user_alert_rules WHERE user_id = ?"
        params = [user_id]
        if enabled_only:
            sql += " AND enabled = 1"
        return [self._decode_alert_rule(row) for row in self.conn.execute(sql, params)]

    def _decode_alert_rule(self, row):
        data = row_to_dict(row)
        data["threshold"] = loads_json(data.pop("threshold_json"), {})
        data["channels"] = loads_json(data.pop("channels_json"), [])
        return data
