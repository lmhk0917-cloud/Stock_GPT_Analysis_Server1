"""Generate validation signals from deterministic event combinations.

Signals are not trading orders. They are structured hypotheses that can be
saved, reviewed, and later evaluated by the paper-trade simulator.
"""


def generate_validation_signal(summary):
    """Return a watch/avoid signal when events form a meaningful setup."""
    events = summary.get("events") or []

    if not events:
        return None

    primary = _get_primary_timeframe(summary)
    latest = primary.get("latest", {})
    box_range = primary.get("box_range") or {}

    current_price = _to_float(latest.get("close"))
    box_high = _to_float(box_range.get("box_high"))
    box_low = _to_float(box_range.get("box_low"))
    event_types = set(event.get("type") for event in events)

    action_hint = "OBSERVE_EVENT"
    confidence_score = 50
    risk_level = "medium"
    reasons = []

    if "RSI_OVERSOLD" in event_types and "NEAR_BOX_LOW" in event_types:
        action_hint = "WATCH_REBOUND"
        confidence_score += 20
        risk_level = "medium"
        reasons.append("RSI oversold and price is near the lower box area.")

    if "NEAR_BOX_LOW" in event_types and "ORDERBOOK_BID_IMBALANCE" in event_types:
        action_hint = "WATCH_REBOUND"
        confidence_score += 18
        risk_level = "medium"
        reasons.append("Lower-box location with bid-side orderbook support can become a rebound setup.")

    if "NEAR_VWAP_SUPPORT" in event_types and "ORDERBOOK_BID_IMBALANCE" in event_types:
        action_hint = "WATCH_PULLBACK"
        confidence_score += 18
        risk_level = "medium"
        reasons.append("VWAP support with bid-side imbalance can become a pullback continuation setup.")

    if "VOLUME_SPIKE" in event_types and "NEAR_BOX_HIGH" in event_types:
        action_hint = "WATCH_BREAKOUT"
        confidence_score += 25
        risk_level = "high"
        reasons.append("Volume spike near the upper box area can become a breakout or a false breakout.")

    if "RSI_OVERBOUGHT" in event_types and "NEAR_BOX_HIGH" in event_types:
        action_hint = "AVOID_CHASE"
        confidence_score += 15
        risk_level = "high"
        reasons.append("RSI overbought near the upper box raises chase-buying risk.")

    if "NEAR_BOX_HIGH" in event_types and "VOLUME_SPIKE" not in event_types:
        action_hint = "AVOID_CHASE"
        confidence_score += 10
        risk_level = "high"
        reasons.append("Price is near the upper box without confirmed volume expansion.")

    if "MA5_MA20_GOLDEN_CROSS" in event_types:
        confidence_score += 5
        reasons.append("MA5 crossed above MA20.")

    if "MA5_MA20_DEAD_CROSS" in event_types:
        confidence_score += 5
        if risk_level == "medium":
            risk_level = "high"
        reasons.append("MA5 crossed below MA20.")

    if "NEAR_VWAP_SUPPORT" in event_types:
        confidence_score += 5
        if action_hint == "OBSERVE_EVENT":
            action_hint = "WATCH_SUPPORT"
        reasons.append("Price is close to VWAP support.")

    if "NEAR_VWAP_RESISTANCE" in event_types:
        risk_level = "high" if risk_level == "medium" else risk_level
        if action_hint == "OBSERVE_EVENT":
            action_hint = "WATCH_RESISTANCE"
        reasons.append("Price is close to VWAP resistance.")

    if "ORDERBOOK_BID_IMBALANCE" in event_types:
        confidence_score += 5
        reasons.append("Bid-side orderbook imbalance supports short-term demand.")

    if "ORDERBOOK_ASK_IMBALANCE" in event_types:
        risk_level = "high"
        if action_hint in ("OBSERVE_EVENT", "WATCH_SUPPORT", "WATCH_PULLBACK"):
            action_hint = "AVOID_SUPPLY"
        reasons.append("Ask-side orderbook imbalance adds short-term supply risk.")

    if "CONSECUTIVE_UP_BARS" in event_types:
        confidence_score += 5
        if action_hint == "OBSERVE_EVENT":
            action_hint = "WATCH_MOMENTUM"
        reasons.append("Recent closes are rising consecutively.")

    if "CONSECUTIVE_DOWN_BARS" in event_types:
        confidence_score += 5
        if action_hint == "OBSERVE_EVENT":
            action_hint = "WATCH_PULLBACK"
        reasons.append("Recent closes are falling consecutively.")

    if "MARKET_SIDECAR_ACTIVE" in event_types:
        confidence_score += 5
        risk_level = "high"
        reasons.append("Market sidecar state requires broader market-risk adjustment.")

    if "MARKET_CIRCUIT_BREAKER_ACTIVE" in event_types or "MARKET_VI_ACTIVE" in event_types:
        action_hint = "AVOID_MARKET_RISK"
        confidence_score += 20
        risk_level = "high"
        reasons.append("Market-wide interruption state makes normal signal reliability lower.")

    if not reasons:
        reasons.append("Event detected, but no strong validation pattern yet.")

    confidence_score = min(max(confidence_score, 0), 100)

    # Price levels are rough validation anchors, not executable order prices.
    stop_loss = _default_stop_loss(current_price, box_low)
    target_1 = _default_target_1(current_price, box_high)
    target_2 = _default_target_2(current_price, box_high)

    return {
        "action_hint": action_hint,
        "confidence_score": confidence_score,
        "risk_level": risk_level,
        "current_price": current_price,
        "stop_loss": stop_loss,
        "target_1": target_1,
        "target_2": target_2,
        "reasons": reasons,
    }


def _get_primary_timeframe(summary):
    """Use 1m as the signal source when multi-timeframe data is present."""
    timeframes = summary.get("timeframes") or {}

    if timeframes.get("1m"):
        return timeframes["1m"]

    for timeframe_summary in timeframes.values():
        return timeframe_summary

    return summary


def _default_stop_loss(current_price, box_low):
    """Prefer lower box as stop; otherwise use a simple fallback percent."""
    if current_price is None:
        return None

    if box_low is not None and box_low < current_price:
        return round(box_low, 2)

    return round(current_price * 0.985, 2)


def _default_target_1(current_price, box_high):
    """Prefer upper box as first target; otherwise use a simple fallback percent."""
    if current_price is None:
        return None

    if box_high is not None and box_high > current_price:
        return round(box_high, 2)

    return round(current_price * 1.015, 2)


def _default_target_2(current_price, box_high):
    """Project a second target beyond the box or use a fallback percent."""
    if current_price is None:
        return None

    if box_high is not None and box_high > current_price:
        return round(box_high + (box_high - current_price), 2)

    return round(current_price * 1.03, 2)


def _to_float(value):
    """Best-effort numeric conversion for indicator values."""
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
