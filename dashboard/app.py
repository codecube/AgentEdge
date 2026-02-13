"""Agent Edge Dashboard — Edge Operations Center.

Real-time visualization of multi-agent edge AI system.
Chat uses A2A ``message/send``; data polling uses REST.
Run: streamlit run dashboard/app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is on sys.path so absolute imports work when
# Streamlit runs this file as a standalone script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from dashboard.components.a2a_conversation import render_a2a_conversation
from dashboard.components.agent_status import render_agent_status
from dashboard.components.anomaly_banner import render_anomaly_banner
from dashboard.components.chat_widget import render_chat_widget
from dashboard.components.lfm_reasoning import render_lfm_reasoning
from dashboard.components.sensor_viz import render_sensor_charts
from dashboard.style import CUSTOM_CSS

# --- Page Config ---
st.set_page_config(
    page_title="Agent Edge",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# --- Config ---
MACMINI_URL = os.getenv("MACMINI_AGENT_URL", "http://localhost:8081")
REFRESH_SECONDS = 2

# --- Auto-refresh (browser-side JS timer — always executes) ---
st_autorefresh(interval=REFRESH_SECONDS * 1000, key="data_refresh")

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "reasoning_events" not in st.session_state:
    st.session_state.reasoning_events = []
if "sensor_readings" not in st.session_state:
    st.session_state.sensor_readings = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


def fetch_all_data() -> dict:
    """Fetch all dashboard data from Mac Mini in one pass.

    The dashboard talks ONLY to the Mac Mini agent.  The Mac Mini tracks
    Jetson availability via heartbeats so the dashboard never needs to
    reach the Jetson directly (which it can't across the network).
    """
    result: dict = {
        "jetson_status": None,
        "macmini_status": None,
        "sensor_readings": [],
        "messages": [],
        "reasoning": [],
    }

    try:
        with httpx.Client(base_url=MACMINI_URL, timeout=3.0) as client:
            # Agent statuses (Mac Mini proxies Jetson status)
            try:
                resp = client.get("/api/agents")
                if resp.status_code == 200:
                    agents = resp.json()
                    result["jetson_status"] = agents.get("jetson")
                    result["macmini_status"] = agents.get("macmini")
            except Exception:
                pass

            # Sensor history
            try:
                resp = client.get("/api/history?limit=60")
                if resp.status_code == 200:
                    result["sensor_readings"] = resp.json()
            except Exception:
                pass

            # A2A messages
            try:
                resp = client.get("/api/messages?limit=50")
                if resp.status_code == 200:
                    result["messages"] = resp.json()
            except Exception:
                pass

            # Reasoning events
            try:
                resp = client.get("/api/reasoning")
                if resp.status_code == 200:
                    result["reasoning"] = resp.json()
            except Exception:
                pass
    except Exception:
        # Mac Mini completely unreachable — everything stays at defaults
        pass

    return result


# --- Header ---
_LOGO_SVG = (Path(__file__).resolve().parent / "assets" / "capgemini_logo_white.svg").read_text()
import base64 as _b64

_logo_b64 = _b64.b64encode(_LOGO_SVG.encode()).decode()
header_html = f"""
<div style="display: flex; align-items: center; gap: 20px; margin-bottom: 8px;">
    <img src="data:image/svg+xml;base64,{_logo_b64}"
         alt="Capgemini" style="height: 52px; margin-top: 10px; opacity: 0.85;" />
    <div style="width: 1px; height: 24px; background: #334155;"></div>
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

# --- Fetch Data (single pass to Mac Mini only) ---
data = fetch_all_data()

if data["sensor_readings"]:
    st.session_state.sensor_readings = data["sensor_readings"]
if data["messages"]:
    st.session_state.messages = data["messages"]
if data["reasoning"]:
    st.session_state.reasoning_events = data["reasoning"]

# --- Anomaly Banner (full-width, above layout) ---
render_anomaly_banner(st.session_state.reasoning_events)

# --- Layout ---

# Row 1: Agent Status + Sensor Metrics
top_left, top_right = st.columns([1, 3])

with top_left:
    render_agent_status(data["jetson_status"], data["macmini_status"])

with top_right:
    render_sensor_charts(st.session_state.sensor_readings)

# Row 2: A2A Messages + LFM Reasoning
bottom_left, bottom_right = st.columns([1, 1])

with bottom_left:
    render_a2a_conversation(st.session_state.messages)

with bottom_right:
    render_lfm_reasoning(st.session_state.reasoning_events)

# --- Sidebar Chat ---
with st.sidebar:
    render_chat_widget(MACMINI_URL)

# --- Footer ---
footer_html = """
<div style="margin-top: 32px; padding-top: 12px; border-top: 1px solid #1e293b;
            display: flex; justify-content: space-between; align-items: center;">
    <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #334155;">
        GOOGLE ADK + A2A + MCP // LFM2.5-1.2B-Thinking // ENS160+AHT21
    </span>
    <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #334155;">
        AI FUTURES LAB
    </span>
</div>
"""
st.markdown(footer_html, unsafe_allow_html=True)
