"""Jetson hybrid server — A2A + dashboard REST + WebSocket + sensor loop.

Combines the ADK A2A agent endpoint with custom dashboard routes and the
background sensor loop in a single FastAPI application.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from agents.jetson import config
from agents.jetson.agent_def import root_agent
from agents.jetson.dashboard_routes import router as dashboard_router
from agents.jetson.sensor_loop import sensor_loop
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from shared import state

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start background tasks on startup, clean up on shutdown."""
    logger.info(
        "Starting Jetson Agent: %s on port %d", config.AGENT_ID, config.AGENT_PORT
    )
    task = asyncio.create_task(sensor_loop())
    yield
    task.cancel()
    logger.info("Shutting down Jetson Agent")


# --- Build app ---

app = FastAPI(title="Jetson Agent - Site A", lifespan=lifespan)

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


# Mount A2A Starlette app as catch-all — serves /.well-known/agent-card.json
# and the JSON-RPC endpoint at POST /
a2a_app = to_a2a(root_agent, port=config.AGENT_PORT)
app.mount("/", a2a_app)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.AGENT_HOST, port=config.AGENT_PORT)
