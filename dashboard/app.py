"""Agent Edge Dashboard — Edge Operations Center.

Real-time visualization of multi-agent edge AI system.
Run: streamlit run dashboard/app.py
"""
from __future__ import annotations

import json
import time

import httpx
import streamlit as st

from dashboard.components.a2a_conversation import render_a2a_conversation
from dashboard.components.agent_status import render_agent_status
from dashboard.components.lfm_reasoning import render_lfm_reasoning
from dashboard.components.sensor_viz import render_sensor_charts
from dashboard.style import CUSTOM_CSS

# --- Page Config ---
st.set_page_config(
    page_title="Agent Edge",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "reasoning_events" not in st.session_state:
    st.session_state.reasoning_events = []
if "sensor_readings" not in st.session_state:
    st.session_state.sensor_readings = []

# --- Config ---
JETSON_URL = "http://localhost:8080"
MACMINI_URL = "http://localhost:8081"
REFRESH_INTERVAL = 1  # seconds


def fetch_agent_status(url: str) -> dict | None:
    """Fetch agent health status."""
    try:
        resp = httpx.get(f"{url}/health", timeout=2.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def fetch_sensor_history() -> list[dict]:
    """Fetch recent sensor readings from Mac Mini."""
    try:
        resp = httpx.get(f"{MACMINI_URL}/api/history?limit=60", timeout=2.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


# --- Header ---
header_html = """
<div style="display: flex; align-items: baseline; gap: 16px; margin-bottom: 8px;">
    <h1 style="margin: 0; font-size: 1.8rem; letter-spacing: -0.04em;">AGENT EDGE</h1>
    <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem;
                 color: #64748b; letter-spacing: 0.05em;">
        MULTI-SITE EDGE INTELLIGENCE
    </span>
</div>
<div style="height: 1px; background: linear-gradient(90deg, #00f0ff44, #ffaa0044, transparent);
            margin-bottom: 24px;"></div>
"""
st.markdown(header_html, unsafe_allow_html=True)

# --- Fetch Data ---
jetson_status = fetch_agent_status(JETSON_URL)
macmini_status = fetch_agent_status(MACMINI_URL)
sensor_readings = fetch_sensor_history()
if sensor_readings:
    st.session_state.sensor_readings = sensor_readings

# --- Layout ---

# Row 1: Agent Status + Sensor Metrics
top_left, top_right = st.columns([1, 3])

with top_left:
    render_agent_status(jetson_status, macmini_status)

with top_right:
    render_sensor_charts(st.session_state.sensor_readings)

# Row 2: A2A Messages + LFM Reasoning
bottom_left, bottom_right = st.columns([1, 1])

with bottom_left:
    render_a2a_conversation(st.session_state.messages)

with bottom_right:
    render_lfm_reasoning(st.session_state.reasoning_events)

# --- Footer ---
footer_html = """
<div style="margin-top: 32px; padding-top: 12px; border-top: 1px solid #1e293b;
            display: flex; justify-content: space-between; align-items: center;">
    <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #334155;">
        MCP + A2A PROTOCOLS // LFM 2.5 1.2B // ENS160+AHT21
    </span>
    <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #334155;">
        AI FUTURES LAB
    </span>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)

# --- Auto-refresh ---
time.sleep(REFRESH_INTERVAL)
st.rerun()
