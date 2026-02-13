# Agent Edge - Multi-Site Edge Intelligence Demo

## Project Overview
Distributed AI agent system: two autonomous agents (Jetson Orin Nano + Mac Mini M2) coordinate via A2A protocol. The Jetson reads an ENS160+AHT21 sensor module (temperature, humidity, eCO2, TVOC, AQI) through an Arduino via MCP protocol. Both agents run Liquid AI LFM2.5-1.2B-Thinking locally. Dashboard via Streamlit.

## Architecture
```
[Arduino ENS160+AHT21] → USB Serial → [MCP Server] → [Jetson Agent] → A2A → [Mac Mini Agent] → [Dashboard]
```

## Key Tech
- **Python 3.10+**, FastAPI, WebSocket, asyncio
- **LLM**: LiquidAI/LFM2.5-1.2B-Thinking via HuggingFace Transformers
- **Sensor**: ENS160 (eCO2, TVOC, AQI) + AHT21 (temp, humidity) over I2C
- **Arduino**: ScioSense_ENS160 + Adafruit_AHTX0 libraries, JSON over serial at 9600 baud
- **Protocols**: MCP (agent-to-system), A2A (agent-to-agent)
- **Storage**: JSON Lines files (no database)
- **Dashboard**: Streamlit + Plotly

## Sensor JSON Schema (flows through all layers)
```json
{"temp": 24.5, "humidity": 65.2, "eco2": 450, "tvoc": 120, "aqi": 1}
```
- `eco2`: ppm (parts per million) — threshold: >1000 = poor air
- `tvoc`: ppb (parts per billion) — threshold: >500 = elevated VOCs
- `aqi`: 1-5 scale (ENS160 index) — threshold: >=4 = unhealthy
- `temp` delta: >5C from previous = anomaly

## Project Structure
```
arduino/sensor_reader/         # Arduino .ino for ENS160+AHT21
mcp_servers/arduino/           # MCP server exposing read_sensor tool
shared/                        # A2A protocol, agent card, LFM client, storage
agents/jetson/                 # Site A agent (sensor + anomaly detection)
agents/macmini/                # Control agent (historical analysis)
dashboard/                     # Streamlit app + components
scripts/                       # Setup and demo launcher scripts
```

## Development Guidelines
- This is a **live demo** for AI Futures Lab — reliability > features
- Keep it simple: two agents, one sensor module, clear collaboration story
- All network calls: retry with exponential backoff (max 3 attempts)
- Use Python `logging` module, JSON Lines format for logs
- ENS160 needs ~1 min warm-up; handle gracefully
- Use Pydantic models for message validation
- Environment variables for IPs/ports, config files for thresholds

## Anomaly Detection (Jetson Agent)
Any of these triggers LFM analysis:
1. Temperature delta > 5C
2. eCO2 > 1000 ppm
3. TVOC > 500 ppb
4. AQI >= 4

## Testing
- Run tests with: `python -m pytest tests/ -v`
- Unit tests for A2A message serialization
- Integration tests with mock MCP server
- End-to-end: sensor → collaboration → dashboard

## Ports
- Jetson agent: 8080
- Mac Mini agent: 8081
- Arduino serial: /dev/ttyACM0 (Jetson), configurable

## Dashboard
Use the **frontend-design** skill when building dashboard components for distinctive, polished UI. The dashboard should be visually compelling for a technical audience demo.
