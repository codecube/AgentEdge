"""Jetson agent configuration."""

import os

AGENT_ID = "jetson-site-a"
AGENT_HOST = os.getenv("JETSON_HOST", "0.0.0.0")
AGENT_PORT = int(os.getenv("JETSON_PORT", "8080"))
MCP_ARDUINO_SERVER = os.getenv(
    "MCP_ARDUINO_SERVER", "./mcp_servers/arduino/server.py"
)
MACMINI_AGENT_URL = os.getenv("MACMINI_AGENT_URL", "http://localhost:8081")
LFM_MODEL = os.getenv("LFM_MODEL", "LiquidAI/LFM-2.5-1B")
SERIAL_PORT = os.getenv("SERIAL_PORT", "/dev/ttyACM0")
SERIAL_BAUD = int(os.getenv("SERIAL_BAUD", "9600"))

SENSOR_POLL_INTERVAL = 5  # seconds

# Anomaly thresholds
TEMP_DELTA_THRESHOLD = 5.0  # degrees celsius
ECO2_THRESHOLD = 1000  # ppm (poor air quality)
TVOC_THRESHOLD = 500  # ppb (elevated VOCs)
AQI_THRESHOLD = 4  # 1-5 scale (unhealthy)

LOG_FILE = os.getenv("JETSON_LOG_FILE", "data/jetson_agent.jsonl")
LOCATION = os.getenv("JETSON_LOCATION", "Site A - Server Room")
