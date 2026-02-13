"""Mac Mini Agent - Control center with historical analysis."""
from __future__ import annotations

import asyncio
import json
import logging
import statistics
from collections import defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import re

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel as PydanticBaseModel

from agents.macmini import config
from shared.a2a_protocol import (
    AgentStatus,
    AnalysisResponse,
    AnalysisResponsePayload,
    Heartbeat,
    MessageType,
    Query,
    QueryPayload,
    QueryResponse,
    SensorObservation,
    parse_message,
    send_message,
)
from shared.agent_card import create_agent_card
from shared.storage import JSONLinesStorage

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)

# State
storage = JSONLinesStorage(config.LOG_FILE)
ws_clients: list[WebSocket] = []
sensor_history: list[dict] = []
peer_card = None
lfm_client = None

SENSOR_FIELDS = ["temperature", "humidity", "eco2", "tvoc", "aqi"]


async def broadcast_ws(data: dict):
    """Broadcast data to all connected WebSocket clients."""
    msg = json.dumps(data)
    disconnected = []
    for ws in ws_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        ws_clients.remove(ws)


async def discover_peer():
    """Try to discover the Jetson agent."""
    global peer_card
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{config.JETSON_AGENT_URL}/health")
            if resp.status_code == 200:
                peer_card = resp.json()
                logger.info("Discovered peer: %s", peer_card.get("agent_id"))
    except Exception as e:
        logger.warning("Peer discovery failed: %s", e)


async def heartbeat_loop():
    """Send periodic heartbeats to peer."""
    while True:
        if peer_card:
            try:
                hb = Heartbeat(**{"from": config.AGENT_ID, "status": AgentStatus.ACTIVE})
                await send_message(config.JETSON_AGENT_URL, hb)
            except Exception:
                pass
        await asyncio.sleep(10)


def compute_statistics() -> dict:
    """Compute statistics across all sensor fields from recent history."""
    if not sensor_history:
        return {}

    stats = {}
    for field in SENSOR_FIELDS:
        values = [r[field] for r in sensor_history if field in r]
        if not values:
            continue
        stats[field] = {
            "mean": round(statistics.mean(values), 2),
            "stdev": round(statistics.stdev(values), 2) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values),
            "count": len(values),
        }
    return stats


async def handle_sensor_observation(msg: SensorObservation):
    """Process incoming sensor observation - store and track history."""
    reading = msg.payload.model_dump()
    reading["timestamp"] = msg.timestamp
    sensor_history.append(reading)

    # Trim history to window
    cutoff_hours = config.HISTORICAL_WINDOW_HOURS
    cutoff_count = cutoff_hours * 3600 // 5  # ~readings at 5s intervals
    if len(sensor_history) > cutoff_count:
        sensor_history[:] = sensor_history[-int(cutoff_count) :]

    storage.append({"event": "sensor_observation", **reading})
    await broadcast_ws({"event": "sensor_observation", "data": reading})


async def handle_analysis_request(data: dict):
    """Process analysis request with historical context and LFM reasoning."""
    payload = data.get("payload", {})
    context = payload.get("context", {})
    current = context.get("current", {})
    anomaly_reasons = context.get("anomaly_reasons", [])

    # Build historical context
    hist_stats = compute_statistics()
    historical_context = {
        "statistics": hist_stats,
        "total_readings": len(sensor_history),
    }

    # Run LFM analysis if available
    lfm_thinking = ""
    answer = "Historical analysis not available (LFM not loaded)"
    confidence = 0.5

    if lfm_client:
        prompt = (
            f"Historical sensor analysis request.\n"
            f"Current reading: temp={current.get('temperature')}C, "
            f"humidity={current.get('humidity')}%, eCO2={current.get('eco2')}ppm, "
            f"TVOC={current.get('tvoc')}ppb, AQI={current.get('aqi')}.\n"
            f"Anomaly reasons: {anomaly_reasons}\n"
            f"Historical stats: {json.dumps(hist_stats, indent=2)}\n"
            f"Jetson agent's analysis: {payload.get('lfm_thinking', 'N/A')}\n"
            f"Based on historical context, is this anomalous? What action is recommended?"
        )
        lfm_thinking = await lfm_client.analyze(prompt)
        answer = lfm_thinking
        confidence = 0.8
    else:
        # Provide basic statistical analysis without LFM
        deviations = []
        for field in SENSOR_FIELDS:
            if field in current and field in hist_stats:
                val = current[field]
                mean = hist_stats[field]["mean"]
                stdev = hist_stats[field]["stdev"]
                if stdev > 0:
                    z = abs(val - mean) / stdev
                    if z > 2:
                        deviations.append(f"{field}={val} is {z:.1f} std devs from mean {mean}")
        if deviations:
            answer = f"Statistical anomalies detected: {'; '.join(deviations)}"
            confidence = 0.6
        else:
            answer = "Readings are within normal statistical range based on historical data."
            confidence = 0.7

    # Send response back
    response = AnalysisResponse(
        **{"from": config.AGENT_ID},
        to=data.get("from", "unknown"),
        in_reply_to=data.get("message_id", ""),
        payload=AnalysisResponsePayload(
            answer=answer,
            confidence=confidence,
            reasoning=historical_context,
            lfm_thinking=lfm_thinking,
        ),
    )

    sender_url = config.JETSON_AGENT_URL
    try:
        await send_message(sender_url, response)
        logger.info("Sent analysis response to %s", data.get("from"))
    except Exception as e:
        logger.warning("Failed to send analysis response: %s", e)

    await broadcast_ws(
        {"event": "analysis_response", "data": response.model_dump(by_alias=True)}
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    logger.info("Starting Mac Mini Agent: %s on port %d", config.AGENT_ID, config.AGENT_PORT)

    global lfm_client
    try:
        from shared.lfm_client import LFMClient

        lfm_client = LFMClient(config.LFM_MODEL)
        logger.info("LFM client loaded")
    except Exception as e:
        logger.warning("LFM client not available: %s", e)

    # Load historical data
    recent = storage.read_recent(config.HISTORICAL_WINDOW_HOURS)
    for record in recent:
        if record.get("event") == "sensor_observation":
            sensor_history.append(record)
    logger.info("Loaded %d historical readings", len(sensor_history))

    asyncio.create_task(discover_peer())
    asyncio.create_task(heartbeat_loop())

    yield

    logger.info("Shutting down Mac Mini Agent")


app = FastAPI(title="Mac Mini Agent - Control Center", lifespan=lifespan)


@app.get("/health")
async def health():
    card = create_agent_card(
        agent_id=config.AGENT_ID,
        host=config.AGENT_HOST,
        port=config.AGENT_PORT,
        capabilities=["historical_analysis", "lfm_reasoning", "dashboard_hosting"],
    )
    return card.model_dump()


@app.get("/api/stats")
async def get_stats():
    """Return current sensor statistics for the dashboard."""
    return {
        "statistics": compute_statistics(),
        "total_readings": len(sensor_history),
        "recent_readings": sensor_history[-20:] if sensor_history else [],
    }


@app.get("/api/history")
async def get_history(limit: int = 100):
    """Return recent sensor readings for the dashboard."""
    return sensor_history[-limit:]


# --- Chat ---


class ChatRequest(PydanticBaseModel):
    question: str


async def _fetch_jetson_live_data() -> dict | None:
    """GET the latest sensor reading from Jetson (2s timeout)."""
    import httpx as _httpx

    try:
        async with _httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{config.JETSON_AGENT_URL}/api/sensor/current")
            if resp.status_code == 200:
                body = resp.json()
                if body.get("status") == "ok":
                    return body["reading"]
    except Exception:
        pass
    return None


async def _send_a2a_query(question: str):
    """Fire-and-forget A2A QUERY so it shows in the dashboard panel."""
    try:
        msg = Query(
            **{"from": config.AGENT_ID},
            to="jetson-site-a",
            payload=QueryPayload(question=question, source="dashboard"),
        )
        await send_message(config.JETSON_AGENT_URL, msg)
    except Exception as e:
        logger.debug("A2A query send failed (non-critical): %s", e)


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

    # General / summary
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


def _build_chat_prompt(question: str, current: dict | None, stats: dict) -> str:
    """Build a structured prompt for LFM with sensor context."""
    if current:
        sensor_block = (
            f"- Temperature: {current.get('temperature')}C\n"
            f"- Humidity: {current.get('humidity')}%\n"
            f"- eCO2: {current.get('eco2')} ppm\n"
            f"- TVOC: {current.get('tvoc')} ppb\n"
            f"- AQI: {current.get('aqi')}/5"
        )
    else:
        sensor_block = "- No live sensor data available"

    stats_lines = []
    count = 0
    for field, s in stats.items():
        stats_lines.append(
            f"  {field}: mean={s['mean']}, stdev={s['stdev']}, min={s['min']}, max={s['max']}"
        )
        count = s.get("count", count)
    stats_formatted = "\n".join(stats_lines) if stats_lines else "  No historical data"

    return (
        "You are an AI assistant for the Agent Edge environmental monitoring system.\n"
        "You have access to sensor data from an ENS160+AHT21 module at Site A.\n\n"
        f"Current sensor data:\n{sensor_block}\n\n"
        f"Historical statistics ({count} readings):\n{stats_formatted}\n\n"
        f"User question: {question}\n\n"
        "Provide a concise, factual answer based on the sensor data above."
    )


async def _generate_chat_answer(
    question: str, current: dict | None, stats: dict
) -> str:
    """Use LFM if available, otherwise fall back to keyword-based data answer."""
    if lfm_client:
        try:
            prompt = _build_chat_prompt(question, current, stats)
            return await lfm_client.analyze(prompt)
        except Exception as e:
            logger.warning("LFM chat failed, falling back to data answer: %s", e)
    return _data_only_answer(question, current, stats)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Answer a natural-language question about sensor data."""
    question = req.question.strip()
    if not question:
        return {"answer": "Please ask a question.", "data_used": {}}

    # Fetch live data from Jetson (best effort)
    current = await _fetch_jetson_live_data()

    # Fall back to latest from our own history
    if current is None and sensor_history:
        current = sensor_history[-1]

    stats = compute_statistics()

    # Fire A2A query for panel visibility (non-blocking)
    asyncio.create_task(_send_a2a_query(question))

    answer = await _generate_chat_answer(question, current, stats)

    # Broadcast the exchange via WebSocket
    await broadcast_ws({
        "event": "chat_query",
        "data": {"question": question, "answer": answer},
    })

    return {
        "answer": answer,
        "data_used": current or {},
    }


@app.post("/a2a/message")
async def receive_message(data: dict):
    """Receive an A2A message from a peer agent."""
    msg_type = data.get("type")
    logger.info("Received A2A message: type=%s", msg_type)
    storage.append({"event": "a2a_received", **data})
    await broadcast_ws({"event": "a2a_message", "data": data})

    if msg_type == MessageType.SENSOR_OBSERVATION:
        msg = parse_message(data)
        await handle_sensor_observation(msg)

    elif msg_type == MessageType.ANALYSIS_REQUEST:
        asyncio.create_task(handle_analysis_request(data))

    elif msg_type == MessageType.QUERY_RESPONSE:
        logger.info("Received query response from %s", data.get("from"))

    elif msg_type == MessageType.HEARTBEAT:
        global peer_card
        if peer_card is None:
            await discover_peer()

    return {"status": "received", "message_id": data.get("message_id")}


@app.websocket("/stream")
async def stream(ws: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    await ws.accept()
    ws_clients.append(ws)
    logger.info("WebSocket client connected (%d total)", len(ws_clients))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_clients.remove(ws)
        logger.info("WebSocket client disconnected (%d total)", len(ws_clients))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.AGENT_HOST, port=config.AGENT_PORT)
