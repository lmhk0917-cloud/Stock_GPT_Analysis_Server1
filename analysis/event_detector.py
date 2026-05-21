"""Rule-based event detection with optional per-user thresholds."""

from app.config import (
    EVENT_BOX_HIGH_POSITION,
    EVENT_BOX_LOW_POSITION,
    EVENT_CONSECUTIVE_BARS,
    EVENT_ORDERBOOK_IMBALANCE,
    EVENT_RSI_HIGH,
    EVENT_RSI_LOW,
    EVENT_VOLUME_RATIO,
    EVENT_VWAP_NEAR_PCT,
)


def detect_gpt_events(summary, settings=None):
    timeframe = _primary_timeframe(summary)
    if not timeframe:
        return []

    events = []
    momentum = timeframe.get("momentum", {})
    volume = timeframe.get("volume", {})
    box_range = timeframe.get("box_range") or {}
    vwap = timeframe.get("vwap", {})
    trend = timeframe.get("trend", {})

    rsi = _to_float(momentum.get("rsi14"))
    if rsi is not None and rsi <= _setting(settings, "EVENT_RSI_LOW", EVENT_RSI_LOW):
        events.append(_event("RSI_OVERSOLD", "1m", rsi, "RSI oversold area"))
    if rsi is not None and rsi >= _setting(settings, "EVENT_RSI_HIGH", EVENT_RSI_HIGH):
        events.append(_event("RSI_OVERBOUGHT", "1m", rsi, "RSI overbought area"))

    ratios = [
        _to_float(volume.get("volume_ratio_5")),
        _to_float(volume.get("volume_ratio_20")),
    ]
    ratios = [value for value in ratios if value is not None]
    if ratios and max(ratios) >= _setting(settings, "EVENT_VOLUME_RATIO", EVENT_VOLUME_RATIO):
        events.append(_event("VOLUME_SPIKE", "1m", round(max(ratios), 3), "Volume ratio spike"))

    position = _to_float(box_range.get("current_position_in_box"))
    if position is not None and position >= _setting(settings, "EVENT_BOX_HIGH_POSITION", EVENT_BOX_HIGH_POSITION):
        events.append(_event("NEAR_BOX_HIGH", "1m", position, "Price near box high"))
    if position is not None and position <= _setting(settings, "EVENT_BOX_LOW_POSITION", EVENT_BOX_LOW_POSITION):
        events.append(_event("NEAR_BOX_LOW", "1m", position, "Price near box low"))

    distance = _to_float(vwap.get("vwap_distance_pct"))
    if distance is not None and abs(distance) <= _setting(settings, "EVENT_VWAP_NEAR_PCT", EVENT_VWAP_NEAR_PCT):
        event_type = "NEAR_VWAP_SUPPORT" if vwap.get("price_above_vwap") else "NEAR_VWAP_RESISTANCE"
        events.append(_event(event_type, "1m", round(distance, 3), "Price is near VWAP"))

    if trend.get("ma5_crossed_above_ma20"):
        events.append(_event("MA5_MA20_GOLDEN_CROSS", "1m", None, "MA5 crossed above MA20"))
    if trend.get("ma5_crossed_below_ma20"):
        events.append(_event("MA5_MA20_DEAD_CROSS", "1m", None, "MA5 crossed below MA20"))

    up = _to_float(trend.get("consecutive_up_bars"))
    down = _to_float(trend.get("consecutive_down_bars"))
    threshold = _setting(settings, "EVENT_CONSECUTIVE_BARS", EVENT_CONSECUTIVE_BARS)
    if up is not None and up >= threshold:
        events.append(_event("CONSECUTIVE_UP_BARS", "1m", up, "Recent closes are rising consecutively"))
    if down is not None and down >= threshold:
        events.append(_event("CONSECUTIVE_DOWN_BARS", "1m", down, "Recent closes are falling consecutively"))

    orderbook = (summary.get("market_context") or {}).get("orderbook") or {}
    imbalance = _to_float(orderbook.get("bid_ask_imbalance"))
    ob_threshold = _setting(settings, "EVENT_ORDERBOOK_IMBALANCE", EVENT_ORDERBOOK_IMBALANCE)
    if imbalance is not None and imbalance >= ob_threshold:
        events.append(_event("ORDERBOOK_BID_IMBALANCE", "realtime", imbalance, "Bid side orderbook imbalance"))
    if imbalance is not None and imbalance <= -ob_threshold:
        events.append(_event("ORDERBOOK_ASK_IMBALANCE", "realtime", imbalance, "Ask side orderbook imbalance"))

    return events


def _primary_timeframe(summary):
    timeframes = summary.get("timeframes") or {}
    return timeframes.get("1m") or next(iter(timeframes.values()), None) or summary


def _event(event_type, timeframe, value, message):
    return {"type": event_type, "timeframe": timeframe, "value": value, "message": message}


def _setting(settings, key, default):
    return (settings or {}).get(key, default)


def _to_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
