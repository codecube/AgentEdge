"""MCP client wrapper for Arduino sensor server."""
from __future__ import annotations

import json
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPArduinoClient:
    """Client for the MCP Arduino sensor server.

    Must be used as an async context manager so the stdio_client cancel scope
    stays within the same asyncio task.
    """

    def __init__(self, serial_port: str, serial_baud: int):
        self.serial_port = serial_port
        self.serial_baud = serial_baud
        self.session: ClientSession | None = None
        self._stdio_cm = None
        self._session_cm = None

    async def __aenter__(self) -> MCPArduinoClient:
        server_params = StdioServerParameters(
            command="python3",
            args=["mcp_servers/arduino/server.py"],
            env={
                "SERIAL_PORT": self.serial_port,
                "SERIAL_BAUD": str(self.serial_baud),
            },
        )
        self._stdio_cm = stdio_client(server_params)
        read_stream, write_stream = await self._stdio_cm.__aenter__()
        self._session_cm = ClientSession(read_stream, write_stream)
        self.session = await self._session_cm.__aenter__()
        await self.session.initialize()
        logger.info("MCP client connected to Arduino server")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session_cm:
            await self._session_cm.__aexit__(exc_type, exc_val, exc_tb)
        if self._stdio_cm:
            await self._stdio_cm.__aexit__(exc_type, exc_val, exc_tb)
        self.session = None

    async def read_sensor(self) -> dict | None:
        """Call the read_sensor MCP tool and return parsed data."""
        if self.session is None:
            logger.warning("MCP session not initialized")
            return None

        try:
            result = await self.session.call_tool("read_sensor", {})
            for content in result.content:
                if content.type == "text":
                    data = json.loads(content.text)
                    if "error" in data:
                        logger.warning("Sensor error: %s", data["error"])
                        return None
                    return data
        except Exception as e:
            logger.error("MCP read_sensor failed: %s", e)
        return None
