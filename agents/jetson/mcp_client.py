"""MCP client wrapper for Arduino sensor server."""
from __future__ import annotations

import json
import logging

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPArduinoClient:
    """Client for the MCP Arduino sensor server."""

    def __init__(self, serial_port: str, serial_baud: int):
        self.serial_port = serial_port
        self.serial_baud = serial_baud
        self.session: ClientSession | None = None
        self._context = None

    async def connect(self):
        """Connect to the MCP Arduino server process."""
        server_params = StdioServerParameters(
            command="python",
            args=["mcp_servers/arduino/server.py"],
            env={
                "SERIAL_PORT": self.serial_port,
                "SERIAL_BAUD": str(self.serial_baud),
            },
        )
        self._read, self._write = await stdio_client(server_params).__aenter__()
        self.session = ClientSession(self._read, self._write)
        await self.session.__aenter__()
        await self.session.initialize()
        logger.info("MCP client connected to Arduino server")

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

    async def close(self):
        """Close the MCP session."""
        if self.session:
            await self.session.__aexit__(None, None, None)
        self.session = None
