"""Mac dashboard REST routes — served alongside the A2A endpoint."""
from __future__ import annotations

import re
import time

from fastapi import APIRouter
from pydantic import BaseModel

from agents.macmini import config
from agents.macmini.tools import compute_statistics
from shared import state

router = APIRouter()


# --- Data endpoints ---


@router.get("/history")
async def get_history(limit: int = 100):
    """Return recent sensor readings for the dashboard."""
    return state.sensor_history[-limit:]


@router.get("/agents")
async def get_agents():
    """Return status of both agents for the dashboard."""
    jetson_online = (
        (time.time() - state.peer_last_seen) < 30 if state.peer_last_seen else False
    )
    jetson_info = state.peer_card if jetson_online else None

    return {
        "jetson": jetson_info,
        "macmini": {
            "agent_id": config.AGENT_ID,
            "capabilities": [
                "historical_analysis",
                "lfm_reasoning",
                "dashboard_hosting",
            ],
            "model": "LiquidAI/LFM2.5-1.2B-Thinking",
            "status": "active",
        },
    }


@router.get("/messages")
async def get_messages(limit: int = 50):
    """Return recent A2A messages for the conversation panel."""
    return state.a2a_messages[-limit:]


@router.get("/reasoning")
async def get_reasoning():
    """Return recent reasoning/anomaly events for the LFM panel."""
    return state.reasoning_events


@router.get("/stats")
async def get_stats():
    """Return current sensor statistics."""
    return {
        "statistics": compute_statistics(),
        "total_readings": len(state.sensor_history),
        "recent_readings": state.sensor_history[-20:] if state.sensor_history else [],
    }


# --- Sensor data push (called by Jetson sensor loop) ---


@router.post("/sensor/push")
async def sensor_push(reading: dict):
    """Receive a sensor reading pushed from the Jetson sensor loop."""
    reading.setdefault("timestamp", "")
    state.sensor_history.append(reading)

    # Mark Jetson as alive
    state.peer_last_seen = time.time()
    if not state.peer_card:
        state.peer_card = {
            "agent_id": "jetson-site-a",
            "capabilities": ["sensor_reading", "anomaly_detection"],
            "model": "LiquidAI/LFM2.5-1.2B-Thinking",
            "status": "active",
        }

    # Trim history
    cutoff_count = int(config.HISTORICAL_WINDOW_HOURS * 3600 / 5)
    if len(state.sensor_history) > cutoff_count:
        state.sensor_history[:] = state.sensor_history[-cutoff_count:]

    await state.broadcast_ws({"event": "sensor_observation", "data": reading})
    return {"status": "ok"}


@router.post("/anomaly/push")
async def anomaly_push(event: dict):
    """Receive an anomaly event pushed from the Jetson sensor loop."""
    state.record_reasoning_event(event)
    await state.broadcast_ws({"event": "reasoning", "data": event})
    return {"status": "ok"}


@router.post("/record-message")
async def record_message(payload: dict):
    """Record an A2A chat exchange from the dashboard."""
    ts = payload.get("timestamp", "")
    state.record_a2a_message(
        "query",
        {
            "type": "query",
            "from": "dashboard",
            "to": config.AGENT_ID,
            "timestamp": ts,
            "payload": {"question": payload.get("question", "")},
        },
    )
    state.record_a2a_message(
        "query_response",
        {
            "type": "query_response",
            "from": config.AGENT_ID,
            "to": "dashboard",
            "timestamp": ts,
            "payload": {"answer": payload.get("answer", "")},
        },
    )
    return {"status": "ok"}


# --- Chat ---


class ChatRequest(BaseModel):
    """Request body for the chat endpoint."""

    question: str


def _data_only_answer(question: str, current: dict | None, stats: dict) -> str:
    """Pattern-match the question against sensor fields for a plain-text answer."""
    q = question.lower()

    if current:
        if re.search(r"humid", q):
            return f"Current humidity at Site A is {current.get('humidity')}%."
        if re.search(r"temp", q):
            return f"Current temperature at Site A is {current.get('temperature')}C."
        if re.search(r"eco2|co2|carbon", q):
            return f"Current eCO2 at Site A is {current.get('eco2')} ppm."
        if re.search(r"tvoc|voc", q):
            return f"Current TVOC at Site A is {current.get('tvoc')} ppb."
        if re.search(r"aqi|air.?quality", q):
            return f"Current AQI at Site A is {current.get('aqi')}/5."

    if current:
        return (
            f"Site A sensor readings: temperature {current.get('temperature')}C, "
            f"humidity {current.get('humidity')}%, eCO2 {current.get('eco2')} ppm, "
            f"TVOC {current.get('tvoc')} ppb, AQI {current.get('aqi')}/5."
        )

    if stats:
        parts = []
        for field, s in stats.items():
            parts.append(f"{field}: mean={s['mean']}")
        return "No live data available. Historical averages: " + ", ".join(parts) + "."

    return "No sensor data is available at this time."


@router.post("/chat")
async def chat(req: ChatRequest):
    """Answer a natural-language question about sensor data.

    Returns a fast data-only answer immediately.  The A2A chat path
    (through the ADK agent) is handled by the dashboard's A2A client.
    """
    from datetime import datetime, timezone

    question = req.question.strip()
    if not question:
        return {"answer": "Please ask a question.", "data_used": {}}

    current: dict | None = None
    if state.sensor_history:
        current = state.sensor_history[-1]

    stats = compute_statistics()
    answer = _data_only_answer(question, current, stats)

    state.record_a2a_message(
        "query",
        {
            "type": "query",
            "from": "dashboard",
            "to": config.AGENT_ID,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"question": question},
        },
    )
    state.record_a2a_message(
        "query_response",
        {
            "type": "query_response",
            "from": config.AGENT_ID,
            "to": "dashboard",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"answer": answer},
        },
    )

    await state.broadcast_ws(
        {"event": "chat_query", "data": {"question": question, "answer": answer}}
    )

    return {"answer": answer, "data_used": current or {}}
