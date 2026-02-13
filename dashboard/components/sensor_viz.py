"""Sensor visualization — real-time charts for ENS160+AHT21 data."""
from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from dashboard.style import AQI_COLORS, AQI_LABELS, PLOTLY_LAYOUT


def render_sensor_charts(readings: list[dict]):
    """Render sensor data charts: temp+humidity, eco2+tvoc, AQI."""
    st.markdown('<div class="section-header">Sensor Data — ENS160+AHT21</div>', unsafe_allow_html=True)

    if not readings:
        st.markdown(
            '<div style="font-family: JetBrains Mono, monospace; color: #64748b; '
            'font-size: 0.8rem; padding: 20px; text-align: center;">'
            "Waiting for sensor data...</div>",
            unsafe_allow_html=True,
        )
        return

    # Latest reading metrics
    latest = readings[-1]
    _render_metric_strip(latest)

    # Charts
    col1, col2 = st.columns(2)

    with col1:
        _render_temp_humidity_chart(readings)

    with col2:
        _render_eco2_tvoc_chart(readings)


def _render_metric_strip(reading: dict):
    """Render the top metric strip with current values."""
    cols = st.columns(5)

    temp = reading.get("temperature", 0)
    humidity = reading.get("humidity", 0)
    eco2 = reading.get("eco2", 0)
    tvoc = reading.get("tvoc", 0)
    aqi = reading.get("aqi", 1)

    with cols[0]:
        st.metric("Temperature", f"{temp:.1f} C")
    with cols[1]:
        st.metric("Humidity", f"{humidity:.1f} %")
    with cols[2]:
        eco2_color = "#ff3366" if eco2 > 1000 else "#ffaa00" if eco2 > 800 else "#00f0ff"
        st.metric("eCO2", f"{eco2} ppm")
    with cols[3]:
        st.metric("TVOC", f"{tvoc} ppb")
    with cols[4]:
        aqi_label = AQI_LABELS.get(aqi, "?")
        aqi_color = AQI_COLORS.get(aqi, "#64748b")
        _render_aqi_gauge(aqi, aqi_label, aqi_color)


def _render_aqi_gauge(aqi: int, label: str, color: str):
    """Render AQI as a segmented gauge bar."""
    segments = ""
    for i in range(1, 6):
        seg_color = color if i <= aqi else "#1e293b"
        segments += f'<div style="height:6px;flex:1;border-radius:2px;background:{seg_color};"></div>'

    html = f"""
    <div style="padding: 0;">
        <div style="font-family: Outfit, sans-serif; font-weight: 600; text-transform: uppercase;
                    font-size: 0.65rem; letter-spacing: 0.08em; color: #64748b; margin-bottom: 4px;">
            Air Quality Index
        </div>
        <div style="font-family: JetBrains Mono, monospace; font-size: 1.6rem; font-weight: 500;
                    color: {color}; line-height: 1.2;">
            {aqi} <span style="font-size: 0.8rem; color: #94a3b8;">{label}</span>
        </div>
        <div style="display: flex; gap: 3px; margin-top: 6px;">
            {segments}
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def _render_temp_humidity_chart(readings: list[dict]):
    """Temperature and humidity line chart."""
    timestamps = [r.get("timestamp", "") for r in readings]
    temps = [r.get("temperature", 0) for r in readings]
    humidities = [r.get("humidity", 0) for r in readings]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps, y=temps,
        name="Temp (C)",
        line=dict(color="#00f0ff", width=2),
        fill="tozeroy",
        fillcolor="rgba(0,240,255,0.05)",
    ))
    fig.add_trace(go.Scatter(
        x=timestamps, y=humidities,
        name="Humidity (%)",
        line=dict(color="#a78bfa", width=2, dash="dot"),
        yaxis="y2",
    ))

    layout = {**PLOTLY_LAYOUT}
    layout["title"] = dict(text="TEMPERATURE + HUMIDITY", font=dict(size=11, color="#64748b"))
    layout["yaxis"] = {**PLOTLY_LAYOUT["yaxis"], "title": "C"}
    layout["yaxis2"] = dict(
        title="%", overlaying="y", side="right",
        gridcolor="#1e293b", zerolinecolor="#1e293b",
    )
    layout["height"] = 260

    fig.update_layout(**layout)
    st.plotly_chart(fig, width="stretch")


def _render_eco2_tvoc_chart(readings: list[dict]):
    """eCO2 and TVOC line chart with threshold markers."""
    timestamps = [r.get("timestamp", "") for r in readings]
    eco2s = [r.get("eco2", 0) for r in readings]
    tvocs = [r.get("tvoc", 0) for r in readings]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=timestamps, y=eco2s,
        name="eCO2 (ppm)",
        line=dict(color="#ffaa00", width=2),
        fill="tozeroy",
        fillcolor="rgba(255,170,0,0.05)",
    ))
    fig.add_trace(go.Scatter(
        x=timestamps, y=tvocs,
        name="TVOC (ppb)",
        line=dict(color="#f472b6", width=2, dash="dot"),
        yaxis="y2",
    ))

    # Threshold line for eCO2
    fig.add_hline(
        y=1000, line=dict(color="#ff3366", width=1, dash="dash"),
        annotation_text="eCO2 threshold",
        annotation_font=dict(color="#ff3366", size=9),
    )

    layout = {**PLOTLY_LAYOUT}
    layout["title"] = dict(text="eCO2 + TVOC", font=dict(size=11, color="#64748b"))
    layout["yaxis"] = {**PLOTLY_LAYOUT["yaxis"], "title": "ppm"}
    layout["yaxis2"] = dict(
        title="ppb", overlaying="y", side="right",
        gridcolor="#1e293b", zerolinecolor="#1e293b",
    )
    layout["height"] = 260

    fig.update_layout(**layout)
    st.plotly_chart(fig, width="stretch")
