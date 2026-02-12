"""Jetson Agent - Site A monitoring with sensor reading and anomaly detection."""
from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from agents.jetson import config
from shared.a2a_protocol import (
    AgentStatus,
    AnalysisRequest,
    AnalysisRequestPayload,
    AnalysisResponse,
    Decision,
    DecisionPayload,
    Heartbeat,
    MessageType,
    SensorObservation,
    SensorPayload,
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
previous_reading: dict | None = None
peer_card = None
lfm_client = None
mcp_client = None


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
    """Try to discover and register the Mac Mini agent."""
    global peer_card
    import httpx

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{config.MACMINI_AGENT_URL}/health")
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
                await send_message(config.MACMINI_AGENT_URL, hb)
            except Exception:
                pass
        await asyncio.sleep(10)


def detect_anomaly(reading: dict) -> list[str]:
    """Check sensor reading against anomaly thresholds. Returns list of reasons."""
    global previous_reading
    reasons = []

    if previous_reading:
        temp_delta = abs(reading["temperature"] - previous_reading["temperature"])
        if temp_delta > config.TEMP_DELTA_THRESHOLD:
            reasons.append(
                f"Temperature delta {temp_delta:.1f}C exceeds {config.TEMP_DELTA_THRESHOLD}C threshold"
            )

    if reading["eco2"] > config.ECO2_THRESHOLD:
        reasons.append(
            f"eCO2 {reading['eco2']}ppm exceeds {config.ECO2_THRESHOLD}ppm threshold"
        )

    if reading["tvoc"] > config.TVOC_THRESHOLD:
        reasons.append(
            f"TVOC {reading['tvoc']}ppb exceeds {config.TVOC_THRESHOLD}ppb threshold"
        )

    if reading["aqi"] >= config.AQI_THRESHOLD:
        reasons.append(
            f"AQI {reading['aqi']} >= {config.AQI_THRESHOLD} (unhealthy)"
        )

    return reasons


async def sensor_loop():
    """Main sensor reading loop."""
    global previous_reading

    while True:
        try:
            reading = None

            # Try MCP client first, fall back to mock
            if mcp_client:
                reading = await mcp_client.read_sensor()
            else:
                logger.debug("No MCP client, skipping sensor read")
                await asyncio.sleep(config.SENSOR_POLL_INTERVAL)
                continue

            if reading is None:
                await asyncio.sleep(config.SENSOR_POLL_INTERVAL)
                continue

            # Log locally
            storage.append({"event": "sensor_reading", **reading})

            # Send observation to peer
            if peer_card:
                obs = SensorObservation(
                    **{"from": config.AGENT_ID},
                    to="macmini-control",
                    payload=SensorPayload(
                        temperature=reading["temperature"],
                        humidity=reading["humidity"],
                        eco2=reading["eco2"],
                        tvoc=reading["tvoc"],
                        aqi=reading["aqi"],
                        location=config.LOCATION,
                    ),
                )
                try:
                    await send_message(config.MACMINI_AGENT_URL, obs)
                except Exception as e:
                    logger.warning("Failed to send observation: %s", e)

                await broadcast_ws(
                    {"event": "sensor_observation", "data": reading}
                )

            # Check for anomalies
            anomaly_reasons = detect_anomaly(reading)
            if anomaly_reasons:
                logger.warning("Anomaly detected: %s", anomaly_reasons)
                storage.append(
                    {"event": "anomaly_detected", "reasons": anomaly_reasons, **reading}
                )

                # Run LFM analysis if available
                lfm_thinking = ""
                if lfm_client:
                    prompt = (
                        f"Analyze this sensor reading: temp={reading['temperature']}C, "
                        f"humidity={reading['humidity']}%, eCO2={reading['eco2']}ppm, "
                        f"TVOC={reading['tvoc']}ppb, AQI={reading['aqi']}. "
                        f"Previous reading: {previous_reading}. "
                        f"Anomaly reasons: {anomaly_reasons}. "
                        f"What is happening and what action should be taken?"
                    )
                    lfm_thinking = await lfm_client.analyze(prompt)

                # Send analysis request to peer
                if peer_card:
                    req = AnalysisRequest(
                        **{"from": config.AGENT_ID},
                        to="macmini-control",
                        payload=AnalysisRequestPayload(
                            question="Anomaly detected in sensor readings. Please analyze with historical context.",
                            context={
                                "current": reading,
                                "previous": previous_reading,
                                "anomaly_reasons": anomaly_reasons,
                            },
                            lfm_thinking=lfm_thinking,
                        ),
                    )
                    try:
                        await send_message(config.MACMINI_AGENT_URL, req)
                    except Exception as e:
                        logger.warning("Failed to send analysis request: %s", e)

                await broadcast_ws(
                    {
                        "event": "anomaly_detected",
                        "reasons": anomaly_reasons,
                        "reading": reading,
                        "lfm_thinking": lfm_thinking,
                    }
                )

            previous_reading = reading

        except Exception as e:
            logger.error("Sensor loop error: %s", e)

        await asyncio.sleep(config.SENSOR_POLL_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown."""
    logger.info("Starting Jetson Agent: %s on port %d", config.AGENT_ID, config.AGENT_PORT)

    # Try to initialize MCP client
    global mcp_client, lfm_client
    try:
        from agents.jetson.mcp_client import MCPArduinoClient

        mcp_client = MCPArduinoClient(config.SERIAL_PORT, config.SERIAL_BAUD)
        await mcp_client.connect()
        logger.info("MCP client connected")
    except Exception as e:
        logger.warning("MCP client not available: %s", e)

    # Try to initialize LFM client
    try:
        from shared.lfm_client import LFMClient

        lfm_client = LFMClient(config.LFM_MODEL)
        logger.info("LFM client loaded")
    except Exception as e:
        logger.warning("LFM client not available: %s", e)

    # Background tasks
    asyncio.create_task(discover_peer())
    asyncio.create_task(heartbeat_loop())
    asyncio.create_task(sensor_loop())

    yield

    logger.info("Shutting down Jetson Agent")


app = FastAPI(title="Jetson Agent - Site A", lifespan=lifespan)


@app.get("/health")
async def health():
    card = create_agent_card(
        agent_id=config.AGENT_ID,
        host=config.AGENT_HOST,
        port=config.AGENT_PORT,
        capabilities=["sensor_reading", "anomaly_detection", "lfm_reasoning"],
    )
    return card.model_dump()


@app.post("/a2a/message")
async def receive_message(data: dict):
    """Receive an A2A message from a peer agent."""
    logger.info("Received A2A message: type=%s", data.get("type"))
    storage.append({"event": "a2a_received", **data})

    msg = parse_message(data)
    await broadcast_ws({"event": "a2a_message", "data": data})

    if isinstance(msg, AnalysisResponse):
        logger.info("Received analysis response: %s", msg.payload.answer)
        # Log the collaborative decision
        decision = Decision(
            participants=[config.AGENT_ID, data.get("from", "unknown")],
            payload=DecisionPayload(
                summary=msg.payload.answer,
                consensus="collaborative_analysis",
                reasoning=msg.payload.reasoning,
            ),
        )
        storage.append(
            {"event": "decision", **decision.model_dump(by_alias=True)}
        )
        await broadcast_ws(
            {"event": "decision", "data": decision.model_dump(by_alias=True)}
        )

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
