"""Mac Mini hybrid server — A2A + dashboard REST + WebSocket.

Combines the ADK A2A agent endpoint with custom dashboard routes in a
single FastAPI application.  The Mac Mini loads historical data on startup
and tracks Jetson liveness via the sensor push endpoint.
"""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from agents.macmini import config
from agents.macmini.agent_def import root_agent
from agents.macmini.dashboard_routes import router as dashboard_router
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from shared import state
from shared.storage import JSONLinesStorage

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load historical data on startup."""
    logger.info(
        "Starting Mac Mini Agent: %s on port %d",
        config.AGENT_ID,
        config.AGENT_PORT,
    )

    # Load historical sensor data from JSONL
    storage = JSONLinesStorage(config.LOG_FILE)
    recent = storage.read_recent(config.HISTORICAL_WINDOW_HOURS)
    for record in recent:
        if record.get("event") == "sensor_observation":
            state.sensor_history.append(record)
    logger.info("Loaded %d historical readings", len(state.sensor_history))

    yield

    logger.info("Shutting down Mac Mini Agent")


# --- Build app ---

app = FastAPI(title="Mac Mini Agent - Control Center", lifespan=lifespan)

# Custom dashboard routes under /api
app.include_router(dashboard_router, prefix="/api")


@app.websocket("/stream")
async def stream(ws: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    await ws.accept()
    state.ws_clients.append(ws)
    logger.info("WebSocket client connected (%d total)", len(state.ws_clients))
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        state.ws_clients.remove(ws)
        logger.info(
            "WebSocket client disconnected (%d total)", len(state.ws_clients)
        )


# Mount A2A Starlette app as catch-all
a2a_app = to_a2a(root_agent, port=config.AGENT_PORT)
app.mount("/", a2a_app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.AGENT_HOST, port=config.AGENT_PORT)
