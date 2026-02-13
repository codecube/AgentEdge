"""Mac Mini agent configuration."""

import os

AGENT_ID = "macmini-control"
AGENT_HOST = os.getenv("MACMINI_HOST", "0.0.0.0")
AGENT_PORT = int(os.getenv("MACMINI_PORT", "8081"))
JETSON_AGENT_URL = os.getenv("JETSON_AGENT_URL", "http://localhost:8080")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
LFM_MODEL = os.getenv("LFM_MODEL", "lfm2.5-thinking")

LOG_FILE = os.getenv("MACMINI_LOG_FILE", "data/macmini_agent.jsonl")
HISTORICAL_WINDOW_HOURS = 24
