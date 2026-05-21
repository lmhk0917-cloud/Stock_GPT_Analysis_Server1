"""Paper-trade evaluator for saved validation signals.

The evaluator does not place trades. It measures what happened after a saved
signal so the event rules can be tuned with evidence.
"""

import argparse
import os
from datetime import datetime, timedelta

from data_store import TickStore


DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "ticks.db")
HORIZONS_MIN = [5, 10, 30, 60]
COMPLETION_GRACE_MINUTES = 5


def main():
    """CLI entrypoint for evaluating pending signals in SQLite."""
    parser = argparse.ArgumentParser(description="Evaluate stored validation signals with future tick data.")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite DB path")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--code", help="Optional stock code filter")
    args = parser.parse_args()

    store = TickStore(db_path=args.db)
    signals = fetch_pending_signals(store, limit=args.limit, code=args.code)

    evaluated = 0
    for signal in signals:
        result = evaluate_signal(store, signal)
        if result:
            store.save_paper_trade_result(result)
            evaluated += 1

    store.close()
    print("evaluated signals:", evaluated)


def fetch_pending_signals(store, limit=100, code=None):
    """Fetch signals that do not yet have an evaluation row."""
    params = []
    where = """
        WHERE NOT EXISTS (
            SELECT 1
            FROM paper_trade_results r
            WHERE r.signal_id = signal_logs.id
        )
    """

    if code:
        where += " AND code = ?"
        params.append(code)

    params.append(limit)

    sql = """
        SELECT *
        FROM signal_logs
        {}
        ORDER BY detected_at ASC
        LIMIT ?
    """.format(where)

    return store.conn.execute(sql, params).fetchall()


def evaluate_signal(store, signal):
    """Evaluate future returns after one signal when enough tick data exists."""
    entry_time = parse_dt(signal["detected_at"])
    entry_price = _to_float(signal["current_price"])

    if not entry_time or not entry_price:
        return None

    end_time = entry_time + timedelta(minutes=max(HORIZONS_MIN))
    fetch_end_time = end_time + timedelta(minutes=COMPLETION_GRACE_MINUTES)
    ticks = fetch_future_ticks(store, signal["code"], entry_time, fetch_end_time)

    if not ticks:
        return None

    last_tick_time = parse_dt(ticks[-1]["received_at"])
    if not last_tick_time or last_tick_time < end_time:
        return None

    evaluation_ticks = ticks_until(ticks, end_time)
    prices = [_to_float(row["price"]) for row in evaluation_ticks if _to_float(row["price"]) is not None]

    if not prices:
        return None

    result = {
        "signal_id": signal["id"],
        "evaluated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "code": signal["code"],
        "entry_time": signal["detected_at"],
        "entry_price": entry_price,
        "max_gain_30m_pct": max_gain_pct(tick_prices_until(ticks, entry_time + timedelta(minutes=30)), entry_price),
        "max_loss_30m_pct": max_loss_pct(tick_prices_until(ticks, entry_time + timedelta(minutes=30)), entry_price),
        "max_gain_60m_pct": round((max(prices) - entry_price) / entry_price * 100, 3),
        "max_loss_60m_pct": round((min(prices) - entry_price) / entry_price * 100, 3),
    }

    for minutes in HORIZONS_MIN:
        horizon_price = find_price_at_or_after(ticks, entry_time + timedelta(minutes=minutes))
        key = "return_{}m_pct".format(minutes)
        result[key] = round((horizon_price - entry_price) / entry_price * 100, 3) if horizon_price else None

    target_1 = _to_float(signal["target_1"]) if "target_1" in signal.keys() else None
    target_2 = _to_float(signal["target_2"]) if "target_2" in signal.keys() else None
    stop_loss = _to_float(signal["stop_loss"]) if "stop_loss" in signal.keys() else None
    hit_info = evaluate_levels(evaluation_ticks, target_1=target_1, target_2=target_2, stop_loss=stop_loss)
    result.update(hit_info)

    return result


def fetch_future_ticks(store, code, start_time, end_time):
    """Read ticks from signal time through the longest evaluation horizon."""
    return store.conn.execute("""
        SELECT received_at, price
        FROM ticks
        WHERE code = ?
          AND received_at >= ?
          AND received_at <= ?
        ORDER BY received_at ASC
    """, (
        code,
        start_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
        end_time.strftime("%Y-%m-%d %H:%M:%S.%f"),
    )).fetchall()


def find_price_at_or_after(ticks, target_time):
    """Find the first tick price at or after a target horizon."""
    for row in ticks:
        received_at = parse_dt(row["received_at"])
        if received_at and received_at >= target_time:
            return _to_float(row["price"])

    return _to_float(ticks[-1]["price"]) if ticks else None


def ticks_until(ticks, end_time):
    """Collect ticks through a horizon timestamp."""
    selected = []
    for row in ticks:
        received_at = parse_dt(row["received_at"])
        price = _to_float(row["price"])
        if received_at and received_at <= end_time and price is not None:
            selected.append(row)
    return selected


def tick_prices_until(ticks, end_time):
    """Collect prices through a horizon timestamp."""
    return [_to_float(row["price"]) for row in ticks_until(ticks, end_time)]


def max_gain_pct(prices, entry_price):
    if not prices:
        return None
    return round((max(prices) - entry_price) / entry_price * 100, 3)


def max_loss_pct(prices, entry_price):
    if not prices:
        return None
    return round((min(prices) - entry_price) / entry_price * 100, 3)


def evaluate_levels(ticks, target_1=None, target_2=None, stop_loss=None):
    """Evaluate whether rough validation levels were touched within 60 minutes."""
    target_1_time = first_touch_time(ticks, target_1, direction="above")
    target_2_time = first_touch_time(ticks, target_2, direction="above")
    stop_time = first_touch_time(ticks, stop_loss, direction="below")

    target_1_hit = target_1_time is not None
    target_2_hit = target_2_time is not None
    stop_loss_hit = stop_time is not None

    if stop_loss_hit and (not target_1_hit or stop_time < target_1_time):
        outcome_label = "stop_before_target"
    elif target_2_hit and (not stop_loss_hit or target_2_time <= stop_time):
        outcome_label = "target_2_before_stop"
    elif target_1_hit and (not stop_loss_hit or target_1_time <= stop_time):
        outcome_label = "target_1_before_stop"
    elif target_2_hit:
        outcome_label = "target_2_after_stop"
    elif target_1_hit:
        outcome_label = "target_1_after_stop"
    else:
        outcome_label = "no_level_hit_60m"

    return {
        "target_1_hit": target_1_hit,
        "target_2_hit": target_2_hit,
        "stop_loss_hit": stop_loss_hit,
        "target_1_hit_at": format_dt(target_1_time),
        "target_2_hit_at": format_dt(target_2_time),
        "stop_loss_hit_at": format_dt(stop_time),
        "outcome_label": outcome_label,
    }


def first_touch_time(ticks, level, direction):
    if level is None:
        return None

    for row in ticks:
        price = _to_float(row["price"])
        received_at = parse_dt(row["received_at"])
        if price is None or received_at is None:
            continue
        if direction == "above" and price >= level:
            return received_at
        if direction == "below" and price <= level:
            return received_at

    return None


def format_dt(value):
    if not value:
        return None
    return value.strftime("%Y-%m-%d %H:%M:%S.%f")


def parse_dt(value):
    """Parse timestamps saved by this project."""
    if not value:
        return None

    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass

    return None


def _to_float(value):
    """Best-effort numeric conversion for SQLite values."""
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    main()
