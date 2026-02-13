"""MCP Arduino Server - Exposes ENS160+AHT21 sensor as MCP tool."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import serial
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [MCP-Arduino] %(levelname)s: %(message)s",
)

SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyUSB0")
SERIAL_BAUD = int(os.getenv("SERIAL_BAUD", "9600"))
SERIAL_TIMEOUT = 8  # seconds — must be > Arduino send interval (5s)

server = Server("arduino-sensor")
serial_conn: serial.Serial | None = None


def get_serial() -> serial.Serial:
    """Get or create serial connection."""
    global serial_conn
    if serial_conn is None or not serial_conn.is_open:
        serial_conn = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=SERIAL_TIMEOUT)
        logger.info("Serial connected: %s @ %d baud", SERIAL_PORT, SERIAL_BAUD)
    return serial_conn


def read_sensor_data() -> dict | None:
    """Read one JSON line from Arduino serial."""
    try:
        conn = get_serial()
        conn.reset_input_buffer()  # discard stale buffered data
        line = conn.readline().decode("utf-8").strip()
        if not line:
            return None
        data = json.loads(line)
        if "error" in data:
            logger.error("Sensor error: %s", data["error"])
            return None
        if data.get("temp") is None:
            return None
        return {
            "temperature": float(data["temp"]),
            "humidity": float(data["humidity"]),
            "eco2": int(data["eco2"]),
            "tvoc": int(data["tvoc"]),
            "aqi": int(data["aqi"]),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except (serial.SerialException, json.JSONDecodeError, KeyError, ValueError) as e:
        logger.error("Sensor read failed: %s", e)
        return None


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="read_sensor",
            description=(
                "Read current ENS160+AHT21 sensor data: temperature (C), "
                "humidity (%), eCO2 (ppm), TVOC (ppb), AQI (1-5 scale)"
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "read_sensor":
        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    data = read_sensor_data()
    if data is None:
        return [
            TextContent(
                type="text",
                text=json.dumps({"error": "Failed to read sensor data"}),
            )
        ]

    logger.info(
        "Sensor reading: temp=%.1fC, hum=%.1f%%, eco2=%dppm, tvoc=%dppb, aqi=%d",
        data["temperature"],
        data["humidity"],
        data["eco2"],
        data["tvoc"],
        data["aqi"],
    )
    return [TextContent(type="text", text=json.dumps(data))]


async def main():
    logger.info("Starting MCP Arduino Server (serial: %s)", SERIAL_PORT)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream, write_stream, server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
