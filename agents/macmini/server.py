"""Mac hybrid server — A2A + dashboard REST + WebSocket.

Combines the ADK A2A agent endpoint with custom dashboard routes in a
single FastAPI application.  The Mac loads historical data on startup
and tracks Jetson liveness via the sensor push endpoint.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from agents.macmini import config
from agents.macmini.agent_def import root_agent
from agents.macmini.dashboard_routes import router as dashboard_router
from shared import state
from shared.a2a_setup import setup_a2a_routes
from shared.storage import JSONLinesStorage

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load historical data and wire A2A routes on startup."""
    logger.info(
        "Starting Mac Agent: %s on port %d",
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

    # Wire A2A JSON-RPC + agent card routes into this FastAPI app
    await setup_a2a_routes(app, root_agent, config.AGENT_PORT)
    logger.info("A2A routes registered")

    yield

    logger.info("Shutting down Mac Agent")


# --- Build app ---

app = FastAPI(title="Mac Agent - Control Center", lifespan=lifespan)

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.AGENT_HOST, port=config.AGENT_PORT)
