# Agent Edge

**Multi-site edge intelligence system where two autonomous AI agents collaborate in real time — no cloud required.**

Agent Edge is a working demonstration built for [Capgemini's AI Futures Lab](https://www.capgemini.com/about-us/who-we-are/innovation-ecosystem/aifutures/) showcasing how edge AI agents can perceive, reason, and collaborate using open protocols. A Jetson Orin Nano reads environmental sensors, detects anomalies, and coordinates with a Mac Mini to reach decisions — all running local LLM inference with [Liquid AI's LFM 2.5](https://www.liquid.ai/models).

## What This Demonstrates

- **Agents as the new APIs** — autonomous agents replacing rigid service-to-service integrations
- **A2A Protocol** — Google's Agent-to-Agent protocol for cross-device agent collaboration
- **MCP Protocol** — Anthropic's Model Context Protocol for agent-to-system integration
- **On-device intelligence** — Liquid AI LFM2.5-1.2B-Thinking running locally on edge hardware
- **Visible reasoning** — watch two AI agents think and collaborate in real time on a live dashboard

## Architecture

![Architecture](docs/diagrams/readme_architecture.png)

## Sensor Data

The ENS160+AHT21 module provides five environmental parameters over I2C:

| Parameter | Unit | Anomaly Threshold |
|-----------|------|-------------------|
| Temperature | °C | > 5°C delta from previous |
| Humidity | % RH | — |
| eCO2 | ppm | > 1000 (poor air quality) |
| TVOC | ppb | > 500 (elevated VOCs) |
| AQI | 1–5 | >= 4 (unhealthy) |

When any threshold is exceeded, both agents run LFM analysis and collaborate to reach a decision.

## Project Structure

```
agent-edge/
├── arduino/sensor_reader/       # Arduino .ino for ENS160+AHT21
├── mcp_servers/arduino/         # MCP server exposing read_sensor tool
├── shared/                      # A2A protocol, agent card, LFM client, storage
│   ├── a2a_protocol.py          # Pydantic message models (6 message types)
│   ├── agent_card.py            # Agent discovery schema
│   ├── lfm_client.py            # LFM 2.5 wrapper with streaming
│   └── storage.py               # JSON Lines append-only storage
├── agents/
│   ├── jetson/                  # Site A: sensor reading + anomaly detection
│   │   ├── agent.py             # FastAPI server on :8080
│   │   ├── cli_chat.py          # Interactive CLI chat (LFM + live sensor)
│   │   ├── config.py            # Thresholds and environment config
│   │   └── mcp_client.py        # MCP client for Arduino server
│   └── macmini/                 # Control: historical analysis + dashboard
│       ├── agent.py             # FastAPI server on :8081
│       └── config.py            # Environment config
├── dashboard/                   # Streamlit real-time dashboard
│   ├── app.py                   # Main app with auto-refresh
│   ├── style.py                 # "Edge Operations Center" theme
│   └── components/              # sensor_viz, a2a_conversation, lfm_reasoning, agent_status
├── docs/                        # Word document + Mermaid diagrams
├── scripts/                     # Setup and launcher scripts
└── tests/                       # Unit tests (23 passing)
```

## Prerequisites

- **Python 3.10+** (3.9 works with `from __future__ import annotations`)
- **Arduino** with ENS160+AHT21 module connected via USB
  - Arduino libraries: `ScioSense_ENS160`, `Adafruit_AHTX0`
- **Jetson Orin Nano** (Site A) or any Linux machine with CUDA (optional)
- **Mac Mini M2** (Control Center) or any machine with MPS/CPU

For local development on a single machine, both agents can run side by side.

## Installation

### 1. Arduino

Flash `arduino/sensor_reader/sensor_reader.ino` to your Arduino using the Arduino IDE. Install the required libraries via Library Manager:

- **ScioSense_ENS160**
- **Adafruit AHTX0**

Wire the ENS160+AHT21 module to the Arduino's I2C pins (SDA/SCL) + VCC + GND. The Arduino outputs JSON at 9600 baud:

```json
{"temp":24.5,"humidity":65.2,"eco2":450,"tvoc":120,"aqi":1}
```

### 2. Jetson Agent (Site A)

```bash
# Clone and enter project
git clone https://github.com/codecube/AgentEdge.git
cd AgentEdge

# Create virtual environment (must be Python 3.10 on Jetson)
python3 -m venv .venv
source .venv/bin/activate

# ⚠️  Install Jetson PyTorch FIRST — the standard pip wheel is CPU-only on aarch64.
# This pulls the CUDA-enabled wheel from NVIDIA's Jetson AI Lab index.
pip install -r agents/jetson/requirements-jetson.txt

# Then install the rest
pip install -r agents/jetson/requirements.txt

# Create data directory
mkdir -p data

# Configure environment
export MACMINI_AGENT_URL=http://<macmini-ip>:8081
export SERIAL_PORT=/dev/ttyUSB0   # Arduino serial port
# export SERIAL_BAUD=9600         # Default, change if needed
# export LFM_MODEL=LiquidAI/LFM2.5-1.2B-Thinking  # Default

# Run the agent
python -m agents.jetson.agent
```

> **PyTorch on Jetson**: The standard `pip install torch` gives you a CPU-only build on aarch64. Without the Jetson-specific wheel, `torch.cuda.is_available()` returns `False` and LFM runs on CPU (~1 tok/s). The `requirements-jetson.txt` file pulls from [NVIDIA's Jetson AI Lab index](https://pypi.jetson-ai-lab.io/jp6/cu126) which provides wheels compiled with CUDA 12.6 for JetPack 6.x. Requires **Python 3.10**. Verify after install:
> ```bash
> python3 -c "import torch; print(torch.cuda.is_available())"  # Should print True
> ```

The Jetson agent will:
- Connect to the Arduino via MCP server
- Read sensor data every 5 seconds
- Send observations to the Mac Mini via A2A
- Detect anomalies and trigger collaborative analysis
- Serve WebSocket stream on `ws://0.0.0.0:8080/stream`

#### Interactive CLI Chat

For demos and debugging, you can also run the standalone CLI chat directly on the Jetson terminal:

```bash
python3 -m agents.jetson.cli_chat
```

This gives you an interactive REPL where you can:
- Type `/sensor` to read live sensor data from the Arduino
- Ask free-text questions — LFM responds with streaming output, using live sensor data as context
- Type `/help` to see all commands, `/quit` to exit

The CLI works with graceful degradation: if no Arduino is connected, chat still works with LFM; if LFM isn't available, sensor reads still work.

### 3. Mac Mini Agent (Control Center)

```bash
# Clone and enter project (if on a different machine)
git clone https://github.com/codecube/AgentEdge.git
cd AgentEdge

# Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r agents/macmini/requirements.txt
pip install -r dashboard/requirements.txt

# Create data directory
mkdir -p data

# Configure environment
export JETSON_AGENT_URL=http://<jetson-ip>:8080
# export LFM_MODEL=LiquidAI/LFM2.5-1.2B-Thinking  # Default

# Run the agent
python -m agents.macmini.agent
```

The Mac Mini agent will:
- Receive and store sensor observations from the Jetson
- Maintain 24-hour rolling statistics for all sensor fields
- Respond to analysis requests with historical context + LFM reasoning
- Serve dashboard data APIs on `:8081`

### 4. Dashboard

On the Mac Mini (or wherever the Mac Mini agent runs):

```bash
streamlit run dashboard/app.py
```

Open `http://localhost:8501` in a browser. The dashboard auto-refreshes every second.

### Quick Start (Single Machine)

For development or demo on one machine:

```bash
bash scripts/run_demo.sh
```

This starts both agents and the dashboard. Press `Ctrl+C` to stop all components.

## Environment Variables

### Jetson Agent

| Variable | Default | Description |
|----------|---------|-------------|
| `MACMINI_AGENT_URL` | `http://localhost:8081` | Mac Mini agent URL |
| `SERIAL_PORT` | `/dev/ttyUSB0` | Arduino serial port |
| `SERIAL_BAUD` | `9600` | Arduino baud rate |
| `LFM_MODEL` | `LiquidAI/LFM2.5-1.2B-Thinking` | HuggingFace model ID |
| `JETSON_HOST` | `0.0.0.0` | Bind address |
| `JETSON_PORT` | `8080` | Agent port |
| `JETSON_LOG_FILE` | `data/jetson_agent.jsonl` | Log file path |
| `JETSON_LOCATION` | `Site A - Server Room` | Location label |

### Mac Mini Agent

| Variable | Default | Description |
|----------|---------|-------------|
| `JETSON_AGENT_URL` | `http://localhost:8080` | Jetson agent URL |
| `LFM_MODEL` | `LiquidAI/LFM2.5-1.2B-Thinking` | HuggingFace model ID |
| `MACMINI_HOST` | `0.0.0.0` | Bind address |
| `MACMINI_PORT` | `8081` | Agent port |
| `MACMINI_LOG_FILE` | `data/macmini_agent.jsonl` | Log file path |

## Testing

```bash
python3 -m pytest tests/ -v
```

39 tests covering A2A protocol serialization, agent cards, chat, storage, and anomaly thresholds.

## Documentation

Full technical documentation is in `docs/Agent_Edge_AI_Futures_Lab.docx`, including:

- Vision chapter on edge agentic AI and agents as the new APIs
- Architecture diagrams (Mermaid source + PNG exports in `docs/diagrams/`)
- Chapter on SLMs, on-device intelligence, and the Capgemini–Liquid AI partnership
- Protocol details, agent design, anomaly detection, and demo scenario

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| Web Framework | FastAPI + Uvicorn |
| Agent Communication | A2A Protocol (HTTP POST + WebSocket) |
| Tool Integration | MCP (Model Context Protocol) |
| LLM | [Liquid AI LFM2.5-1.2B-Thinking](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct) |
| Dashboard | Streamlit + Plotly |
| Storage | JSON Lines (no database) |
| Sensor | ENS160 + AHT21 (I2C) |

## Related Articles

- [Agents Are the New APIs](https://www.linkedin.com/pulse/agents-new-apis-pedro-falc%C3%A3o-costa-1ydpf/) — Pedro Falcao Costa
- [The A2A Protocol: Google Is Here and Changes Everything](https://www.linkedin.com/pulse/a2a-protocol-google-here-changes-everything-pedro-falc%C3%A3o-costa-fggff/) — Pedro Falcao Costa
- [Capgemini and Liquid AI Partnership](https://www.capgemini.com/capgemini-and-liquid-ai/)
- [Capgemini AI Futures Lab](https://www.capgemini.com/about-us/who-we-are/innovation-ecosystem/aifutures/)

## License

Internal — Capgemini AI Futures Lab
