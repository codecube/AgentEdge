"""LFM reasoning display — token stream with air quality analysis."""
from __future__ import annotations

import streamlit as st


def render_lfm_reasoning(reasoning_events: list[dict]):
    """Render the LFM reasoning token stream panel."""
    st.markdown('<div class="section-header">LFM Reasoning Stream</div>', unsafe_allow_html=True)

    if not reasoning_events:
        html = (
            '<div class="lfm-stream">'
            '<span style="color: #475569;">Waiting for anomaly to trigger LFM analysis...</span>'
            '<span class="lfm-cursor"></span>'
            "</div>"
        )
        st.markdown(html, unsafe_allow_html=True)
        return

    # Show the most recent reasoning event
    latest = reasoning_events[-1]
    lfm_text = latest.get("lfm_thinking", "")
    reasons = latest.get("reasons", [])
    reading = latest.get("reading", {})

    # Build the reasoning display
    parts = []

    # Show trigger context
    if reasons:
        trigger_html = '<span style="color: #ff3366; font-weight: 500;">ANOMALY TRIGGER</span><br>'
        for r in reasons:
            trigger_html += f'<span style="color: #ffaa00;">  {r}</span><br>'
        parts.append(trigger_html)

    # Show current reading context
    if reading:
        ctx = (
            f'<span style="color: #64748b;">Reading:</span> '
            f'<span style="color: #00f0ff;">temp={reading.get("temperature", "?")}C</span> '
            f'<span style="color: #a78bfa;">hum={reading.get("humidity", "?")}%</span> '
            f'<span style="color: #ffaa00;">eCO2={reading.get("eco2", "?")}ppm</span> '
            f'<span style="color: #f472b6;">TVOC={reading.get("tvoc", "?")}ppb</span> '
            f'<span style="color: {_aqi_color(reading.get("aqi", 1))};">AQI={reading.get("aqi", "?")}</span>'
        )
        parts.append(ctx + "<br><br>")

    # Show LFM output
    if lfm_text:
        parts.append(f'<span style="color: #e2e8f0;">{_escape_html(lfm_text)}</span>')
        parts.append('<span class="lfm-cursor"></span>')
    else:
        parts.append(
            '<span style="color: #475569;">LFM model not loaded — '
            "showing statistical analysis only</span>"
        )

    html = '<div class="lfm-stream">' + "\n".join(parts) + "</div>"
    st.markdown(html, unsafe_allow_html=True)

    # Decision history
    if len(reasoning_events) > 1:
        st.markdown(
            '<div style="margin-top: 12px; font-family: Outfit, sans-serif; '
            'font-weight: 600; font-size: 0.65rem; text-transform: uppercase; '
            'letter-spacing: 0.08em; color: #64748b; margin-bottom: 8px;">'
            "Recent Decisions</div>",
            unsafe_allow_html=True,
        )
        history_lines = []
        for evt in reasoning_events[-5:]:
            ts = evt.get("reading", {}).get("timestamp", "")
            time_str = ts[11:19] if len(ts) > 19 else "—"
            reasons_short = evt.get("reasons", ["—"])
            history_lines.append(
                f'<div style="font-family: JetBrains Mono, monospace; font-size: 0.7rem; '
                f'color: #64748b; line-height: 1.6;">'
                f'<span style="color: #475569;">{time_str}</span> '
                f'<span style="color: #ffaa00;">{reasons_short[0] if reasons_short else "—"}</span>'
                f"</div>"
            )
        st.markdown("\n".join(history_lines), unsafe_allow_html=True)


def _aqi_color(aqi: int) -> str:
    colors = {1: "#22c55e", 2: "#84cc16", 3: "#ffaa00", 4: "#f97316", 5: "#ff3366"}
    return colors.get(aqi, "#64748b")


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
