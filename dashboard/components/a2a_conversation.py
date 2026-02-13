"""A2A conversation display — scrolling message feed between agents.

Renders both legacy custom messages (from ``/api/messages``) and
A2A SDK-format messages (with ``role`` / ``parts``).
"""
from __future__ import annotations

import streamlit as st


def render_a2a_conversation(messages: list[dict]):
    """Render the A2A message feed."""
    st.markdown('<div class="section-header">A2A Message Flow</div>', unsafe_allow_html=True)

    if not messages:
        st.markdown(
            '<div class="msg-feed" style="text-align: center; color: #64748b;">'
            "No messages yet — waiting for agent communication...</div>",
            unsafe_allow_html=True,
        )
        return

    # Build message HTML
    lines = []
    for msg in messages[-50:]:  # Last 50 messages
        lines.append(_format_message(msg))

    html = '<div class="msg-feed">' + "\n".join(lines) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def _extract_parts_text(parts: list[dict]) -> str:
    """Extract text from A2A message parts list."""
    texts = []
    for part in parts:
        text = part.get("text", "")
        if text:
            texts.append(text)
    return " ".join(texts)[:100]


def _format_message(msg: dict) -> str:
    """Format a single message as styled HTML.

    Supports both the custom format (event/data/type/from/payload) and
    A2A SDK format (role/parts/messageId).
    """
    # --- A2A SDK format (role + parts) ---
    data = msg.get("data", msg)
    if "role" in data and "parts" in data:
        role = data["role"]
        text = _extract_parts_text(data.get("parts", []))
        color = "#a78bfa" if role == "user" else "#00f0ff"
        label = "USER" if role == "user" else "AGENT"
        return (
            f'<div><span class="msg-system">[{label}]</span> '
            f'<span style="color:{color};">{text}</span></div>'
        )

    # --- Legacy custom format ---
    event = msg.get("event", msg.get("type", "unknown"))
    timestamp = data.get("timestamp", "")

    # Shorten timestamp to HH:MM:SS
    time_str = timestamp[11:19] if len(timestamp) > 19 else timestamp[:8]

    from_agent = data.get("from", "")
    msg_type = data.get("type", event)

    # Determine agent color class
    if "jetson" in from_agent.lower():
        agent_class = "msg-jetson"
        agent_label = "JETSON"
    elif "macmini" in from_agent.lower() or "mac" in from_agent.lower():
        agent_class = "msg-macmini"
        agent_label = "MAC"
    else:
        agent_class = "msg-system"
        agent_label = "SYSTEM"

    # Format based on message type
    if "anomaly" in event:
        reasons = msg.get("reasons", data.get("anomaly_reasons", []))
        detail = "; ".join(reasons) if reasons else "anomaly detected"
        return (
            f'<div><span style="color:#475569;">{time_str}</span> '
            f'<span class="msg-anomaly">!! ANOMALY</span> '
            f'<span style="color:#ff336699;">{detail}</span></div>'
        )

    if msg_type == "sensor_observation":
        payload = data.get("payload", data)
        temp = payload.get("temperature", "?")
        eco2 = payload.get("eco2", "?")
        aqi = payload.get("aqi", "?")
        return (
            f'<div><span style="color:#475569;">{time_str}</span> '
            f'<span class="{agent_class}">[{agent_label}]</span> '
            f'<span style="color:#475569;">observation</span> '
            f'<span style="color:#94a3b8;">{temp}C / {eco2}ppm / AQI {aqi}</span></div>'
        )

    if msg_type == "analysis_request":
        return (
            f'<div><span style="color:#475569;">{time_str}</span> '
            f'<span class="{agent_class}">[{agent_label}]</span> '
            f'<span style="color:#ffaa00;">analysis_request</span> '
            f'<span style="color:#94a3b8;">requesting historical context</span></div>'
        )

    if msg_type == "analysis_response":
        payload = data.get("payload", {})
        answer = payload.get("answer", "")[:80]
        conf = payload.get("confidence", 0)
        return (
            f'<div><span style="color:#475569;">{time_str}</span> '
            f'<span class="{agent_class}">[{agent_label}]</span> '
            f'<span style="color:#22c55e;">analysis_response</span> '
            f'<span style="color:#94a3b8;">({conf:.0%}) {answer}</span></div>'
        )

    if msg_type == "query":
        payload = data.get("payload", {})
        question = payload.get("question", "")[:80]
        return (
            f'<div><span style="color:#475569;">{time_str}</span> '
            f'<span class="{agent_class}">[{agent_label}]</span> '
            f'<span style="color:#a78bfa;">query</span> '
            f'<span style="color:#94a3b8;">{question}</span></div>'
        )

    if msg_type == "query_response":
        payload = data.get("payload", {})
        answer = payload.get("answer", "")[:80]
        return (
            f'<div><span style="color:#475569;">{time_str}</span> '
            f'<span class="{agent_class}">[{agent_label}]</span> '
            f'<span style="color:#a78bfa;">query_response</span> '
            f'<span style="color:#94a3b8;">{answer}</span></div>'
        )

    if msg_type == "heartbeat":
        return (
            f'<div><span style="color:#475569;">{time_str}</span> '
            f'<span class="{agent_class}">[{agent_label}]</span> '
            f'<span style="color:#334155;">heartbeat</span></div>'
        )

    # Generic fallback
    return (
        f'<div><span style="color:#475569;">{time_str}</span> '
        f'<span class="{agent_class}">[{agent_label}]</span> '
        f'<span style="color:#64748b;">{msg_type}</span></div>'
    )
