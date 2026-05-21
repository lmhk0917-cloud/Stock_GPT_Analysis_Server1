"""Private per-user memory and chat history storage."""

from core.database import dumps_json, loads_json, row_to_dict, utc_now


class UserMemoryStore:
    def __init__(self, conn):
        self.conn = conn

    def add_memory(self, user_id, content, memory_type="preference", visibility="private"):
        now = utc_now()
        cur = self.conn.execute(
            """
            INSERT INTO user_memory(user_id, memory_type, content_json, visibility, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, memory_type, dumps_json(content), visibility, now, now),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_memory(self, user_id):
        rows = self.conn.execute(
            "SELECT * FROM user_memory WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        return [self._decode_memory(row) for row in rows]

    def create_chat_session(self, user_id, title="New chat"):
        now = utc_now()
        cur = self.conn.execute(
            "INSERT INTO chat_sessions(user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (user_id, title, now, now),
        )
        self.conn.commit()
        return cur.lastrowid

    def add_chat_message(self, session_id, role, content, token_count=None):
        cur = self.conn.execute(
            "INSERT INTO chat_messages(session_id, role, content, token_count, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, token_count, utc_now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def list_chat_messages(self, session_id):
        rows = self.conn.execute(
            "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY id",
            (session_id,),
        )
        return [row_to_dict(row) for row in rows]

    def _decode_memory(self, row):
        data = row_to_dict(row)
        data["content"] = loads_json(data.pop("content_json"), {})
        return data
