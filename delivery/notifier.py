"""User-aware notification delivery for console and later Telegram use."""

from core.audit_store import AuditStore


class UserNotifier:
    def __init__(self, conn):
        self.conn = conn
        self.audit_store = AuditStore(conn)

    def notify_matching_users(self, summary, events):
        if not events:
            return []

        users = self.conn.execute(
            """
            SELECT DISTINCT u.*
            FROM users u
            JOIN user_watchlists w ON w.user_id = u.id
            WHERE u.is_active = 1
              AND w.enabled = 1
              AND w.market = ?
              AND w.code = ?
            """,
            (summary.get("market", "KRX"), summary.get("code")),
        ).fetchall()

        results = []
        for user in users:
            for event in events:
                message = self._message(summary, event)
                self.audit_store.save_notification(
                    user["id"],
                    "console",
                    summary.get("market", "KRX"),
                    summary.get("code"),
                    event.get("type"),
                    message,
                    "sent",
                )
                results.append({
                    "user_id": user["id"],
                    "login_id": user["login_id"],
                    "channel": "console",
                    "event_type": event.get("type"),
                    "status": "sent",
                    "message": message,
                })
        return results

    def _message(self, summary, event):
        return "[{}] {}({}) {}".format(
            event.get("type", "EVENT"),
            summary.get("name", ""),
            summary.get("code", ""),
            event.get("message", ""),
        )
