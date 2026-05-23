"""Persistence for shared analysis and delivery audit records."""

from core.database import dumps_json, loads_json, row_to_dict, utc_now


class AuditStore:
    def __init__(self, conn):
        self.conn = conn

    def upsert_symbol(self, market, code, name, currency="KRW", provider="mock", enabled=True):
        self.conn.execute(
            """
            INSERT INTO market_symbols(market, code, name, currency, provider, enabled)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(market, code)
            DO UPDATE SET name = excluded.name, provider = excluded.provider, enabled = excluded.enabled
            """,
            (market, code, name, currency, provider, int(enabled)),
        )
        self.conn.commit()

    def save_price_bar(self, market, code, timeframe, bar, provider="mock"):
        self.conn.execute(
            """
            INSERT OR REPLACE INTO market_prices(
              market, code, timeframe, timestamp, open, high, low, close, volume, provider
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                market,
                code,
                timeframe,
                str(bar["timestamp"]),
                float(bar["open"]),
                float(bar["high"]),
                float(bar["low"]),
                float(bar["close"]),
                float(bar["volume"]),
                provider,
            ),
        )

    def save_analysis_result(self, market, code, summary, gpt_result=None, model=None, prompt_version="mock-v1"):
        cur = self.conn.execute(
            """
            INSERT INTO analysis_results(market, code, analyzed_at, summary_json, gpt_result, model, prompt_version)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (market, code, utc_now(), dumps_json(summary), gpt_result, model, prompt_version),
        )
        self.conn.commit()
        return cur.lastrowid

    def save_event(self, market, code, event, summary):
        self.conn.execute(
            """
            INSERT INTO event_logs(market, code, detected_at, event_type, timeframe, value, summary_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                market,
                code,
                utc_now(),
                event.get("type", "UNKNOWN"),
                event.get("timeframe", "1m"),
                event.get("value"),
                dumps_json(summary),
            ),
        )
        self.conn.commit()

    def save_notification(self, user_id, channel, market, code, event_type, message, status):
        self.conn.execute(
            """
            INSERT INTO notification_logs(user_id, channel, market, code, event_type, message, status, sent_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, channel, market, code, event_type, message, status, utc_now()),
        )
        self.conn.commit()

    def save_gpt_call(
        self,
        started_at,
        finished_at,
        status,
        requested_count,
        symbols,
        model,
        usage=None,
        result_preview=None,
    ):
        usage = usage or {}
        cur = self.conn.execute(
            """
            INSERT INTO gpt_call_logs(
              started_at, finished_at, status, requested_count, symbols_json, model,
              prompt_tokens, completion_tokens, total_tokens, result_preview
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                started_at,
                finished_at,
                status,
                requested_count,
                dumps_json(symbols),
                model,
                usage.get("prompt_tokens"),
                usage.get("completion_tokens"),
                usage.get("total_tokens"),
                (result_preview or "")[:500],
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def reports_for_user(self, user_id):
        rows = self.conn.execute(
            """
            SELECT ar.*
            FROM analysis_results ar
            JOIN user_watchlists uw
              ON uw.market = ar.market AND uw.code = ar.code
            WHERE uw.user_id = ? AND uw.enabled = 1
            ORDER BY ar.analyzed_at DESC
            """,
            (user_id,),
        )
        return [row_to_dict(row) for row in rows]

    def latest_reports_for_user(self, user_id, limit=5):
        rows = self.conn.execute(
            """
            SELECT ar.*
            FROM analysis_results ar
            JOIN user_watchlists uw
              ON uw.market = ar.market AND uw.code = ar.code
            WHERE uw.user_id = ? AND uw.enabled = 1
            ORDER BY ar.analyzed_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        )
        reports = []
        for row in rows:
            data = row_to_dict(row)
            data["summary"] = loads_json(data.pop("summary_json"), {})
            reports.append(data)
        return reports

    def usage_summary(self, user_id=None):
        params = []
        user_filter = ""
        if user_id is not None:
            user_filter = "WHERE user_id = ?"
            params.append(user_id)

        request_count = self.conn.execute(
            "SELECT COUNT(*) FROM api_request_logs {}".format(user_filter),
            params,
        ).fetchone()[0]
        notification_count = self.conn.execute(
            "SELECT COUNT(*) FROM notification_logs {}".format(user_filter),
            params,
        ).fetchone()[0]
        order_count = self.conn.execute(
            "SELECT COUNT(*) FROM order_requests {}".format(user_filter),
            params,
        ).fetchone()[0]

        gpt_tokens = self.conn.execute(
            "SELECT COALESCE(SUM(total_tokens), 0) FROM gpt_call_logs"
        ).fetchone()[0]

        users = self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        watchlists = self.conn.execute("SELECT COUNT(*) FROM user_watchlists").fetchone()[0]
        analyses = self.conn.execute("SELECT COUNT(*) FROM analysis_results").fetchone()[0]
        events = self.conn.execute("SELECT COUNT(*) FROM event_logs").fetchone()[0]

        return {
            "users": users,
            "watchlists": watchlists,
            "analysis_results": analyses,
            "events": events,
            "api_requests": request_count,
            "notifications": notification_count,
            "orders": order_count,
            "gpt_total_tokens_all_users": gpt_tokens,
        }
