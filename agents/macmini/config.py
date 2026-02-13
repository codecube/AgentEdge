"""Mac Mini agent configuration."""

import os

AGENT_ID = "macmini-control"
AGENT_HOST = os.getenv("MACMINI_HOST", "0.0.0.0")
AGENT_PORT = int(os.getenv("MACMINI_PORT", "8081"))
JETSON_AGENT_URL = os.getenv("JETSON_AGENT_URL", "http://localhost:8080")
LFM_MODEL = os.getenv("LFM_MODEL", "LiquidAI/LFM2.5-1.2B-Thinking")

LOG_FILE = os.getenv("MACMINI_LOG_FILE", "data/macmini_agent.jsonl")
HISTORICAL_WINDOW_HOURS = 24
