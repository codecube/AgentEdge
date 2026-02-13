"""Jetson sensor loop — background asyncio task.

Owns the MCP connection (serial port is exclusive).  Reads sensor data,
stores locally, pushes to Mac Mini via REST, and broadcasts via WebSocket.
"""
from __future__ import annotations

import asyncio
import logging

import httpx

from agents.jetson import config
from agents.jetson.tools import detect_anomalies
from shared import state
from shared.storage import JSONLinesStorage

logger = logging.getLogger(__name__)


async def sensor_loop() -> None:
    """Main sensor reading loop.

    The MCP client is connected here (not in lifespan) so the anyio cancel
    scope created by stdio_client stays within this single asyncio task.
    """
    storage = JSONLinesStorage(config.LOG_FILE)
    mcp_client = None

    try:
        from agents.jetson.mcp_client import MCPArduinoClient

        mcp_cm = MCPArduinoClient(config.SERIAL_PORT, config.SERIAL_BAUD)
        mcp_client = await mcp_cm.__aenter__()
        logger.info("MCP client connected in sensor loop")
    except Exception as e:
        logger.warning("MCP client not available: %s", e)

    while True:
        try:
            reading = None

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

            # Check for anomalies
            result = detect_anomalies(
                temperature=reading["temperature"],
                humidity=reading["humidity"],
                eco2=reading["eco2"],
                tvoc=reading["tvoc"],
                aqi=reading["aqi"],
            )
            if result["is_anomaly"]:
                logger.warning("Anomaly detected: %s", result["reasons"])
                storage.append(
                    {
                        "event": "anomaly_detected",
                        "reasons": result["reasons"],
                        **reading,
                    }
                )
                await state.broadcast_ws(
                    {
                        "event": "anomaly_detected",
                        "reasons": result["reasons"],
                        "reading": reading,
                    }
                )

            # Update shared state
            state.previous_reading = reading

            # Push to Mac Mini via REST
            await _push_to_macmini(reading)

            await state.broadcast_ws(
                {"event": "sensor_observation", "data": reading}
            )

        except Exception as e:
            logger.error("Sensor loop error: %s", e)

        await asyncio.sleep(config.SENSOR_POLL_INTERVAL)


async def _push_to_macmini(reading: dict) -> None:
    """Push a sensor reading to the Mac Mini's REST endpoint."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{config.MACMINI_AGENT_URL}/api/sensor/push",
                json=reading,
            )
    except Exception as e:
        logger.warning("Failed to push reading to Mac Mini: %s", e)
