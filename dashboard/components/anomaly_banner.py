"""Full-width anomaly alert banner — renders between header and main layout."""
from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st


def render_anomaly_banner(reasoning_events: list[dict]) -> None:
    """Show a crimson alert banner when recent anomalies exist.

    Only renders when at least one reasoning event has a
    ``reading.timestamp`` within the last 60 seconds.  Returns early
    (renders nothing) otherwise — zero visual overhead normally.
    """
    if not reasoning_events:
        return

    now = datetime.now(timezone.utc)
    recent: list[dict] = []

    for evt in reasoning_events:
        ts_str = evt.get("reading", {}).get("timestamp", "")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            if (now - ts).total_seconds() <= 60:
                recent.append(evt)
        except (ValueError, TypeError):
            continue

    if not recent:
        return

    count = len(recent)
    latest = recent[-1]
    reading = latest.get("reading", {})

    # Collect all unique reasons across recent events
    all_reasons: list[str] = []
    for evt in recent:
        for r in evt.get("reasons", []):
            if r not in all_reasons:
                all_reasons.append(r)

    # Count badge
    badge = (
        f'<span style="background: #ff3366; color: #fff; font-family: \'JetBrains Mono\', monospace;'
        f" font-size: 0.7rem; font-weight: 700; padding: 2px 8px; border-radius: 10px;"
        f' margin-left: 10px;">{count}</span>'
        if count > 1
        else ""
    )

    # Reason pills
    pills = " ".join(
        f'<span style="display: inline-block; background: #ff336622; color: #ff6690;'
        f" font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 500;"
        f' padding: 2px 10px; border-radius: 3px; margin: 2px 4px 2px 0;">{_escape(r)}</span>'
        for r in all_reasons
    )

    # Sensor value strip
    values = (
        f'<span style="color: #00f0ff;">TEMP {reading.get("temperature", "—")}C</span>'
        f'<span style="color: #334155; margin: 0 6px;">|</span>'
        f'<span style="color: #a78bfa;">HUM {reading.get("humidity", "—")}%</span>'
        f'<span style="color: #334155; margin: 0 6px;">|</span>'
        f'<span style="color: #ffaa00;">eCO2 {reading.get("eco2", "—")}ppm</span>'
        f'<span style="color: #334155; margin: 0 6px;">|</span>'
        f'<span style="color: #f472b6;">TVOC {reading.get("tvoc", "—")}ppb</span>'
        f'<span style="color: #334155; margin: 0 6px;">|</span>'
        f'<span style="color: {_aqi_color(reading.get("aqi", 1))};">AQI {reading.get("aqi", "—")}</span>'
    )

    html = f"""
    <div class="anomaly-banner">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
            <span style="font-family: 'Outfit', sans-serif; font-weight: 700;
                         font-size: 0.85rem; color: #ff3366; letter-spacing: 0.04em;
                         text-transform: uppercase;">ANOMALY DETECTED</span>
            {badge}
        </div>
        <div style="margin-bottom: 6px;">{pills}</div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem;
                    letter-spacing: 0.02em;">{values}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def _aqi_color(aqi: int) -> str:
    colors = {1: "#22c55e", 2: "#84cc16", 3: "#ffaa00", 4: "#f97316", 5: "#ff3366"}
    return colors.get(aqi, "#64748b")


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
