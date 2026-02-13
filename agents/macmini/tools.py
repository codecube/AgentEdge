"""Mac agent tool functions for ADK.

Pure functions that the LLM agent can call as tools.  They read from
shared state (populated by sensor observations) and from JSONL storage.
"""
from __future__ import annotations

import statistics as stats_mod

from shared import state


def compute_statistics() -> dict:
    """Compute statistics for all sensor fields from recent history.

    Returns:
        Dictionary mapping each sensor field (temperature, humidity, eco2,
        tvoc, aqi) to its mean, stdev, min, max, and count.
        Empty dict if no history is available.
    """
    if not state.sensor_history:
        return {}

    result: dict = {}
    for field in state.SENSOR_FIELDS:
        values = [r[field] for r in state.sensor_history if field in r]
        if not values:
            continue
        result[field] = {
            "mean": round(stats_mod.mean(values), 2),
            "stdev": round(stats_mod.stdev(values), 2) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "count": len(values),
        }
    return result


def get_recent_history(limit: int = 20) -> list:
    """Get the most recent sensor readings.

    Args:
        limit: Maximum number of readings to return. Defaults to 20.

    Returns:
        List of sensor reading dictionaries, most recent last.
    """
    return state.sensor_history[-limit:]


def get_anomaly_summary() -> dict:
    """Get a summary of recent anomaly and reasoning events.

    Returns:
        Dictionary with 'count' and 'events' list of reasoning events.
    """
    return {
        "count": len(state.reasoning_events),
        "events": state.reasoning_events,
    }
