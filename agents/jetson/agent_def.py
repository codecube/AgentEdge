"""Jetson ADK agent definition.

Defines the LlmAgent with LiteLlm (Ollama) and sensor tools.
The read_sensor tool returns cached data from the sensor loop —
not a direct MCP call — because the serial port is exclusive.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from agents.jetson import config
from agents.jetson.tools import detect_anomalies, get_latest_reading, get_sensor_history

INSTRUCTION = (
    "You are the Jetson Site A monitoring agent for the Agent Edge system. "
    f"You are deployed at {config.LOCATION} with an ENS160+AHT21 sensor module.\n\n"
    "Your capabilities:\n"
    "- Read live sensor data (temperature, humidity, eCO2, TVOC, AQI)\n"
    "- Detect anomalies against thresholds "
    f"(temp delta >{config.TEMP_DELTA_THRESHOLD}C, "
    f"eCO2 >{config.ECO2_THRESHOLD}ppm, "
    f"TVOC >{config.TVOC_THRESHOLD}ppb, "
    f"AQI >={config.AQI_THRESHOLD})\n"
    "- Retrieve historical sensor readings\n\n"
    "When asked about sensor data, always call the appropriate tool. "
    "Provide concise, factual answers."
)

root_agent = LlmAgent(
    name="jetson_site_a",
    model=LiteLlm(model="ollama_chat/sam860/lfm2.5:1.2b-Q8_0"),
    description="Site A sensor monitoring agent on Jetson Orin Nano. "
    "Reads air quality sensors and detects environmental anomalies.",
    instruction=INSTRUCTION,
    tools=[get_latest_reading, detect_anomalies, get_sensor_history],
)
