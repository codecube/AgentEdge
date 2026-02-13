"""Mac ADK agent definition.

Defines the control LlmAgent with LiteLlm (Ollama), analysis tools,
and a RemoteA2aAgent sub-agent pointing at the Jetson.
"""
from __future__ import annotations

import os

from google.adk.agents import LlmAgent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.models.lite_llm import LiteLlm

from agents.macmini import config
from agents.macmini.tools import compute_statistics, get_anomaly_summary, get_recent_history

JETSON_URL = os.getenv("JETSON_AGENT_URL", config.JETSON_AGENT_URL)

jetson_remote = RemoteA2aAgent(
    name="jetson_site_a",
    description=(
        "Remote agent on Jetson Orin Nano at Site A. "
        "Reads live air quality sensors (temperature, humidity, eCO2, TVOC, AQI) "
        "and detects environmental anomalies."
    ),
    agent_card=f"{JETSON_URL}/.well-known/agent-card.json",
)

INSTRUCTION = (
    "You are the Mac control agent for the Agent Edge system. "
    "You coordinate with the Jetson sensor agent and provide historical analysis.\n\n"
    "Your capabilities:\n"
    "- Compute statistics across sensor fields\n"
    "- Retrieve recent sensor history\n"
    "- Summarize anomaly events\n"
    "- Delegate to the Jetson agent for live sensor readings\n\n"
    "When asked about current readings, delegate to the jetson_site_a agent. "
    "When asked about trends or statistics, use your own tools. "
    "Provide concise, factual answers."
)

root_agent = LlmAgent(
    name="macmini_control",
    model=LiteLlm(model="ollama_chat/lfm2.5-thinking"),
    description="Control agent on Mac. "
    "Performs historical analysis and coordinates with remote sensor agents.",
    instruction=INSTRUCTION,
    tools=[compute_statistics, get_recent_history, get_anomaly_summary],
    sub_agents=[jetson_remote],
)
