"""Agent status panel — live connection indicators.

Displays agent status from the Mac's ``/api/agents`` REST endpoint.
A2A agent cards are available at ``/.well-known/agent-card.json`` but the
Mac proxies Jetson status so the dashboard doesn't need direct access.
"""
from __future__ import annotations

import streamlit as st


def render_agent_status(jetson_status: dict | None, macmini_status: dict | None):
    """Render agent connection status cards."""
    st.markdown('<div class="section-header">Agent Status</div>', unsafe_allow_html=True)

    _render_agent_card(
        name="Jetson Orin Nano",
        role="Site A",
        status=jetson_status,
        accent="#00f0ff",
    )
    st.markdown('<div style="margin-top: 12px;"></div>', unsafe_allow_html=True)
    _render_agent_card(
        name="Mac M2",
        role="Control",
        status=macmini_status,
        accent="#ffaa00",
    )


def _render_agent_card(name: str, role: str, status: dict | None, accent: str):
    """Render a single agent status card."""
    is_online = status is not None
    indicator = "status-online" if is_online else "status-offline"
    state_text = "ONLINE" if is_online else "OFFLINE"
    state_color = "#22c55e" if is_online else "#ff3366"

    # Support both old format (agent_id) and A2A card format (name)
    agent_id = (
        status.get("agent_id") or status.get("name", "—") if status else "—"
    )
    model = status.get("model", "—") if status else "—"
    caps_list = (status.get("capabilities") or status.get("skills") or []) if status else []
    if isinstance(caps_list, list) and caps_list and isinstance(caps_list[0], dict):
        caps = ", ".join(s.get("name", "") for s in caps_list)
    elif isinstance(caps_list, list):
        caps = ", ".join(str(c) for c in caps_list)
    else:
        caps = "—"

    html = f"""
    <div style="
        background: #151d2e;
        border: 1px solid #1e293b;
        border-top: 2px solid {accent};
        border-radius: 4px;
        padding: 16px;
        font-family: 'Outfit', sans-serif;
    ">
        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
            <div>
                <div style="font-weight: 700; font-size: 0.95rem; color: #e2e8f0;">{name}</div>
                <div style="font-size: 0.7rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.08em;">{role}</div>
            </div>
            <div style="display: flex; align-items: center;">
                <span class="{indicator}"></span>
                <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: {state_color}; font-weight: 500;">{state_text}</span>
            </div>
        </div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #64748b; line-height: 1.8;">
            <div><span style="color: #475569;">ID</span> <span style="color: #94a3b8;">{agent_id}</span></div>
            <div><span style="color: #475569;">MODEL</span> <span style="color: #94a3b8;">{model}</span></div>
            <div><span style="color: #475569;">CAPS</span> <span style="color: #94a3b8;">{caps}</span></div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
