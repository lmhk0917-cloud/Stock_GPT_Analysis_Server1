"""Persistence for shared analysis and delivery audit records."""

from datetime import datetime

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

    def latest_watchlist_status_for_user(self, user_id, limit=20):
        watch_rows = self.conn.execute(
            """
            SELECT market, code, name
            FROM user_watchlists
            WHERE user_id = ? AND enabled = 1
            ORDER BY sort_order, id
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        statuses = []
        for watch in watch_rows:
            report = self.conn.execute(
                """
                SELECT *
                FROM analysis_results
                WHERE market = ? AND code = ?
                ORDER BY analyzed_at DESC, id DESC
                LIMIT 1
                """,
                (watch["market"], watch["code"]),
            ).fetchone()
            price = self.conn.execute(
                """
                SELECT timestamp, close, volume, provider
                FROM market_prices
                WHERE market = ? AND code = ?
                ORDER BY timestamp DESC, id DESC
                LIMIT 1
                """,
                (watch["market"], watch["code"]),
            ).fetchone()
            item = row_to_dict(watch)
            if report:
                report_data = row_to_dict(report)
                report_data["summary"] = loads_json(report_data.pop("summary_json"), {})
                item["latest_report"] = report_data
            else:
                item["latest_report"] = None
            item["latest_price"] = row_to_dict(price)
            statuses.append(item)
        return statuses

    def latest_evidence_pack_for_user(self, user_id, limit=10, tick_limit=300):
        watch_rows = self.conn.execute(
            """
            SELECT market, code, name
            FROM user_watchlists
            WHERE user_id = ? AND enabled = 1
            ORDER BY sort_order, id
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        symbols = []
        for watch in watch_rows:
            symbol = row_to_dict(watch)
            tick_evidence = self._tick_evidence(symbol["market"], symbol["code"], tick_limit=tick_limit)
            report = self._latest_report(symbol["market"], symbol["code"])
            latest_price = self._latest_price(symbol["market"], symbol["code"])
            recent_events = self._recent_events(symbol["market"], symbol["code"], limit=5)
            missing_data = []
            if not tick_evidence:
                missing_data.append("kiwoom_legacy_ticks")
            if not report:
                missing_data.append("latest_analysis_report")
            if not latest_price and not tick_evidence:
                missing_data.append("latest_price")
            data_quality = {
                "tick_source": "kiwoom_legacy_ticks" if tick_evidence else "missing",
                "latest_report": "available" if report else "missing",
                "latest_price": "available" if latest_price else "missing",
                "missing_data": missing_data,
            }
            if tick_evidence:
                data_quality["latest_tick_age_sec"] = tick_evidence.get("latest_tick_age_sec")
                data_quality["stale_tick"] = (
                    tick_evidence.get("latest_tick_age_sec") is None
                    or tick_evidence.get("latest_tick_age_sec") > 300
                )
            symbols.append({
                "market": symbol["market"],
                "code": symbol["code"],
                "name": symbol["name"],
                "tick_evidence": tick_evidence,
                "latest_price": latest_price,
                "latest_report": report,
                "recent_events": recent_events,
                "data_quality": data_quality,
            })
        return {
            "schema": "stock_gpt_evidence_pack_v1",
            "generated_at": utc_now(),
            "user_id": user_id,
            "symbols": symbols,
            "guidance": (
                "Use this as evidence, not as an order instruction. If tick data is missing "
                "or stale, say so before giving advice."
            ),
        }

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

    def _tick_evidence(self, market, code, tick_limit=300):
        rows = self.conn.execute(
            """
            SELECT code, trade_time, price, change_rate, acc_volume, tick_volume,
                   open_price, high_price, low_price, strength, received_at, imported_at
            FROM kiwoom_legacy_ticks
            WHERE market = ? AND code = ?
            ORDER BY received_at DESC, id DESC
            LIMIT ?
            """,
            (market, code, tick_limit),
        ).fetchall()
        if not rows:
            return None
        ticks = [row_to_dict(row) for row in reversed(rows)]
        latest = ticks[-1]
        first_price = _to_float(ticks[0].get("price"))
        latest_price = _to_float(latest.get("price"))
        price_change_pct = None
        if first_price not in (None, 0) and latest_price is not None:
            price_change_pct = round((latest_price - first_price) / first_price * 100, 4)

        total_volume = sum(_to_float(tick.get("tick_volume")) or 0 for tick in ticks)
        price_volume = sum(
            (_to_float(tick.get("price")) or 0) * (_to_float(tick.get("tick_volume")) or 0)
            for tick in ticks
        )
        vwap = round(price_volume / total_volume, 4) if total_volume else None
        strengths = [_to_float(tick.get("strength")) for tick in ticks if _to_float(tick.get("strength")) is not None]
        latest_dt = _parse_datetime(latest.get("received_at"))
        age_sec = int((datetime.now() - latest_dt).total_seconds()) if latest_dt else None

        return {
            "source": "kiwoom_legacy_ticks",
            "sample_size": len(ticks),
            "first_received_at": ticks[0].get("received_at"),
            "latest_received_at": latest.get("received_at"),
            "latest_tick_age_sec": age_sec,
            "latest_trade_time": latest.get("trade_time"),
            "first_price": first_price,
            "latest_price": latest_price,
            "price_change_pct_in_sample": price_change_pct,
            "latest_change_rate": _to_float(latest.get("change_rate")),
            "sample_tick_volume_sum": total_volume,
            "sample_vwap": vwap,
            "latest_strength": _to_float(latest.get("strength")),
            "avg_strength": round(sum(strengths) / len(strengths), 4) if strengths else None,
            "high_price_in_sample": _max_float(tick.get("price") for tick in ticks),
            "low_price_in_sample": _min_float(tick.get("price") for tick in ticks),
        }

    def _latest_report(self, market, code):
        row = self.conn.execute(
            """
            SELECT *
            FROM analysis_results
            WHERE market = ? AND code = ?
            ORDER BY analyzed_at DESC, id DESC
            LIMIT 1
            """,
            (market, code),
        ).fetchone()
        if not row:
            return None
        data = row_to_dict(row)
        data["summary"] = loads_json(data.pop("summary_json"), {})
        return data

    def _latest_price(self, market, code):
        row = self.conn.execute(
            """
            SELECT timestamp, close, volume, provider
            FROM market_prices
            WHERE market = ? AND code = ?
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
            """,
            (market, code),
        ).fetchone()
        return row_to_dict(row)

    def _recent_events(self, market, code, limit=5):
        rows = self.conn.execute(
            """
            SELECT detected_at, event_type, timeframe, value, summary_json
            FROM event_logs
            WHERE market = ? AND code = ?
            ORDER BY detected_at DESC, id DESC
            LIMIT ?
            """,
            (market, code, limit),
        ).fetchall()
        events = []
        for row in rows:
            data = row_to_dict(row)
            data["summary"] = loads_json(data.pop("summary_json"), {})
            events.append(data)
        return events


def _parse_datetime(value):
    if not value:
        return None
    text = str(value).strip().replace("T", " ").replace("Z", "")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                pass
    return None


def _to_float(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _max_float(values):
    numbers = [_to_float(value) for value in values]
    numbers = [value for value in numbers if value is not None]
    return max(numbers) if numbers else None


def _min_float(values):
    numbers = [_to_float(value) for value in values]
    numbers = [value for value in numbers if value is not None]
    return min(numbers) if numbers else None
