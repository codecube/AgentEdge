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
from shared import state
from shared.a2a_setup import setup_a2a_routes

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

    # Wire A2A JSON-RPC + agent card routes into this FastAPI app
    await setup_a2a_routes(app, root_agent, config.AGENT_PORT)
    logger.info("A2A routes registered")

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.AGENT_HOST, port=config.AGENT_PORT)
