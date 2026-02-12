# Project: Agent Edge - Multi-Site Edge Intelligence Demo

## Overview
Build a distributed AI agent system demonstrating thought leadership in edge AI. Two autonomous agents (Jetson Orin Nano + Mac Mini M2) coordinate using A2A protocol, with one agent reading sensors via MCP protocol. Both agents run Liquid AI LFM 2.5 (1.2B) thinking models locally. This is a demo for AI Futures Lab showcasing edge intelligence, agent collaboration, and interoperability protocols.

## Project Context
- **Purpose**: Demonstrate multi-location agent coordination with local LLM reasoning
- **Target Audience**: AI Futures Lab - technical audience interested in edge AI and agent systems
- **Hardware**: Jetson Orin Nano (Site A), Mac Mini M2 (Control Center), Arduino with ENS160+AHT21 sensor module
- **Key Differentiators**: Pure edge (no cloud), A2A protocol, MCP integration, visible LFM reasoning

## Architecture

```
[Arduino ENS160+AHT21] → USB Serial → [MCP Arduino Server] 
                                      ↓ MCP Protocol
                              [Jetson Agent (Site A)]
                                      ↓
                                   A2A Protocol
                                      ↓
                              [Mac Mini Agent (Control)]
                                      ↓
                              [Streamlit Dashboard]

Protocols Used:
- MCP: Agent-to-System integration (Arduino sensors via I2C)
- A2A: Agent-to-Agent collaboration (peer-to-peer)

Storage: Simple JSON Lines files (no database complexity)
LLM: Liquid AI LFM 2.5 1.2B via HuggingFace on both agents
```

## Technology Stack

### Both Agents
- Python 3.10+
- FastAPI (for A2A HTTP endpoints)
- WebSocket (for real-time streaming)
- HuggingFace Transformers (LFM 2.5 model)
- asyncio (for concurrent operations)

### Jetson Specific
- `mcp` Python package (MCP client)
- `pyserial` (for Arduino communication in MCP server)

### Mac Mini Specific
- Streamlit (dashboard)
- Plotly (real-time graphs)

### Arduino
- `ScioSense_ENS160` library (eCO2, TVOC, AQI via I2C)
- `Adafruit_AHTX0` library (temperature + humidity via I2C)
- I2C communication (SDA/SCL)
- JSON output over serial

## Project Structure

```
agent-edge/
├── README.md
├── requirements.txt
├── ARCHITECTURE.md
├── DEMO_SCRIPT.md
│
├── arduino/
│   └── sensor_reader/
│       └── sensor_reader.ino          # ENS160+AHT21 sensor code (I2C)
│
├── mcp_servers/
│   └── arduino/
│       ├── server.py                   # MCP Arduino Server
│       └── requirements.txt
│
├── shared/
│   ├── a2a_protocol.py                 # A2A message types & utilities
│   ├── agent_card.py                   # Agent Card schema
│   ├── lfm_client.py                   # LFM 2.5 wrapper
│   └── storage.py                      # JSON logging utilities
│
├── agents/
│   ├── jetson/
│   │   ├── agent.py                    # Main Jetson agent
│   │   ├── mcp_client.py               # MCP client wrapper
│   │   ├── config.py                   # Configuration
│   │   └── requirements.txt
│   │
│   └── macmini/
│       ├── agent.py                    # Main Mac Mini agent
│       ├── config.py                   # Configuration
│       └── requirements.txt
│
├── dashboard/
│   ├── app.py                          # Streamlit dashboard
│   ├── components/
│   │   ├── sensor_viz.py               # Sensor graphs
│   │   ├── a2a_conversation.py         # Message flow display
│   │   ├── lfm_reasoning.py            # LFM thinking display
│   │   └── agent_status.py             # Agent health
│   └── requirements.txt
│
└── scripts/
    ├── setup_jetson.sh                 # Jetson setup script
    ├── setup_macmini.sh                # Mac Mini setup script
    └── run_demo.sh                     # Demo launcher
```

## Core Requirements

### 1. MCP Arduino Server (`mcp_servers/arduino/server.py`)

**Purpose**: Expose Arduino sensor as MCP tool

**Requirements**:
- Read ENS160+AHT21 sensor data from USB serial (`/dev/ttyACM0` on Jetson)
- Expose MCP tool: `read_sensor`
- Return JSON: `{temperature: float, humidity: float, eco2: int, tvoc: int, aqi: int, timestamp: ISO8601}`
- Handle serial errors gracefully
- Follow MCP protocol specification

**Implementation Notes**:
- Use `mcp` Python package: `from mcp.server import Server`
- Parse Arduino JSON output from serial (5 fields: temp, humidity, eco2, tvoc, aqi)
- Add timeout handling for serial reads
- Log all sensor readings with timestamps
- Note: ENS160 needs ~1 min warm-up; readings during warm-up may be unreliable

### 2. A2A Protocol (`shared/a2a_protocol.py`)

**Purpose**: Standardized agent-to-agent communication

**Message Types**:
```python
# Agent discovery
{
  "type": "agent_card",
  "agent_id": str,
  "capabilities": List[str],
  "model": str,
  "endpoints": {
    "a2a": str,
    "health": str,
    "stream": str
  },
  "status": "active" | "degraded" | "offline"
}

# Sensor observation
{
  "type": "sensor_observation",
  "from": str,
  "to": str,
  "message_id": str,
  "timestamp": str,
  "payload": {
    "sensor": str,
    "temperature": float,
    "humidity": float,
    "eco2": int,        # ppm (parts per million)
    "tvoc": int,        # ppb (parts per billion)
    "aqi": int,         # 1-5 scale (ENS160 air quality index)
    "location": str
  }
}

# Analysis request (for collaboration)
{
  "type": "analysis_request",
  "from": str,
  "to": str,
  "message_id": str,
  "timestamp": str,
  "payload": {
    "question": str,
    "context": dict,
    "lfm_thinking": str  # LFM reasoning chain
  }
}

# Analysis response
{
  "type": "analysis_response",
  "from": str,
  "to": str,
  "in_reply_to": str,  # message_id of request
  "timestamp": str,
  "payload": {
    "answer": str,
    "confidence": float,
    "reasoning": dict,
    "lfm_thinking": str
  }
}

# Collaborative decision
{
  "type": "decision",
  "participants": List[str],
  "decision_id": str,
  "timestamp": str,
  "payload": {
    "summary": str,
    "consensus": str,
    "reasoning": dict
  }
}

# Heartbeat
{
  "type": "heartbeat",
  "from": str,
  "timestamp": str,
  "status": str
}
```

**Requirements**:
- HTTP POST endpoint at `/a2a/message` for receiving messages
- WebSocket endpoint at `/stream` for real-time updates
- Message validation with Pydantic models
- Automatic message_id generation (UUID)
- Message logging to JSON Lines file
- Retry logic with exponential backoff
- Peer discovery on startup

### 3. LFM 2.5 Integration (`shared/lfm_client.py`)

**Purpose**: Wrapper for Liquid AI LFM 2.5 1.2B model

**Requirements**:
- Load from HuggingFace: `LiquidAI/LFM-2.5-1B` (or correct model ID)
- Support streaming token generation
- Prompt templates for:
  - Anomaly detection: "Analyze this sensor reading: temp={temp}°C, humidity={humidity}%, eCO2={eco2}ppm, TVOC={tvoc}ppb, AQI={aqi}. Previous: ..."
  - Historical analysis: "Based on these historical readings: {...}, are the current values anomalous?"
  - Collaborative reasoning: "Agent A says: {...}. Agent B says: {...}. Synthesize..."
- Return structured output: `{conclusion: str, thinking: str, confidence: float}`
- Token-by-token streaming for dashboard visualization
- GPU acceleration if available (Jetson CUDA, Mac MPS)

**Implementation Notes**:
```python
from transformers import AutoModelForCausalLM, AutoTokenizer

class LFMClient:
    def __init__(self, model_name="LiquidAI/LFM-2.5-1B"):
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto",  # Auto GPU/CPU
            torch_dtype="auto"
        )
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
    
    async def analyze_streaming(self, prompt: str):
        # Yield tokens as they're generated
        # Return final structured output
        pass
```

### 4. Jetson Agent (`agents/jetson/agent.py`)

**Purpose**: Site A monitoring agent with sensor reading

**Responsibilities**:
1. **Startup**:
   - Initialize MCP client to Arduino server
   - Start A2A server (FastAPI on port 8080)
   - Broadcast Agent Card
   - Discover Mac Mini agent
   
2. **Sensor Reading Loop** (every 5 seconds):
   - Call MCP tool: `read_sensor`
   - Log reading locally (JSON Lines)
   - Send `sensor_observation` A2A message to Mac Mini
   
3. **Anomaly Detection**:
   - Multi-parameter anomaly triggers (any one triggers analysis):
     - Temperature delta > 5°C from previous reading
     - eCO2 > 1000 ppm (poor indoor air quality)
     - TVOC > 500 ppb (elevated volatile organic compounds)
     - AQI >= 4 (unhealthy air quality on 1-5 scale)
   - If anomaly: Run LFM analysis with all sensor fields as context
   - Send `analysis_request` A2A message to Mac Mini
   - Wait for Mac Mini response
   - Log collaborative decision
   
4. **A2A Message Handling**:
   - Receive analysis responses from Mac Mini
   - Process heartbeats
   - Stream all activity to WebSocket clients (dashboard)

**Configuration** (`agents/jetson/config.py`):
```python
AGENT_ID = "jetson-site-a"
AGENT_PORT = 8080
MCP_ARDUINO_SERVER = "./mcp_servers/arduino/server.py"
MACMINI_AGENT_URL = "http://192.168.1.x:8081"  # Configure actual IP
LFM_MODEL = "LiquidAI/LFM-2.5-1B"
SENSOR_POLL_INTERVAL = 5  # seconds
# Anomaly thresholds
TEMP_DELTA_THRESHOLD = 5    # degrees celsius
ECO2_THRESHOLD = 1000       # ppm (poor air quality)
TVOC_THRESHOLD = 500        # ppb (elevated VOCs)
AQI_THRESHOLD = 4           # 1-5 scale (unhealthy)
LOG_FILE = "jetson_agent.jsonl"
```

### 5. Mac Mini Agent (`agents/macmini/agent.py`)

**Purpose**: Control center agent with historical analysis

**Responsibilities**:
1. **Startup**:
   - Start A2A server (FastAPI on port 8081)
   - Broadcast Agent Card
   - Discover Jetson agent
   
2. **Message Handling**:
   - Receive `sensor_observation` from Jetson → log locally
   - Receive `analysis_request` from Jetson:
     - Query local historical data (last 24 hours)
     - Run LFM analysis with historical context
     - Send `analysis_response` back to Jetson
   
3. **Historical Data**:
   - Maintain rolling window of sensor readings (all fields: temp, humidity, eco2, tvoc, aqi)
   - Calculate statistics per field (mean, std dev, min, max)
   - Provide multi-parameter context for anomaly analysis (e.g., "CO2 is spiking while temperature is stable")
   
4. **Dashboard Hosting**:
   - Stream all A2A messages to dashboard via WebSocket
   - Provide API endpoints for dashboard data queries

**Configuration** (`agents/macmini/config.py`):
```python
AGENT_ID = "macmini-control"
AGENT_PORT = 8081
JETSON_AGENT_URL = "http://jetson-ip:8080"  # Configure actual IP
LFM_MODEL = "LiquidAI/LFM-2.5-1B"
LOG_FILE = "macmini_agent.jsonl"
HISTORICAL_WINDOW_HOURS = 24
```

### 6. Streamlit Dashboard (`dashboard/app.py`)

**Purpose**: Real-time visualization of agent system

**Requirements**:

**Layout**:
```
┌──────────────────────────────────────────────────────────┐
│  Agent Edge - Multi-Site Intelligence                    │
├──────────────────┬───────────────────────────────────────┤
│ Agent Status     │  Sensor Data                          │
│ ┌──────────────┐ │  ┌─────────────────┬────────────────┐ │
│ │Jetson: ✓     │ │  │[Temp + Humidity] │ [eCO2 + TVOC] │ │
│ │MacMini: ✓    │ │  │ Temp: 24.5°C    │ eCO2: 450 ppm │ │
│ │Connected: 2s │ │  │ Hum:  65.2%     │ TVOC: 120 ppb │ │
│ └──────────────┘ │  ├─────────────────┴────────────────┤ │
│                  │  │ AQI: 1 (Good) ■□□□□              │ │
│                  │  └──────────────────────────────────┘ │
├──────────────────┴───────────────────────────────────────┤
│ A2A Message Flow                                         │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ [Jetson] → observation: 24.5°C, 450ppm eCO2, AQI 1  │ │
│ │ [Jetson] → analysis_request: CO2 spike?              │ │
│ │ [MacMini] → analysis_response: ventilation needed    │ │
│ └──────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────┤
│ LFM Reasoning (Token Stream)                             │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ Analyzing sensor readings...                         │ │
│ │ eCO2: 1200ppm (above 1000 threshold), temp stable... │ │
│ │ CO2 spike with stable temp suggests poor ventilation │ │
│ └──────────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────────┤
│ Decision History                                         │
│ • 10:32 - CO2 elevated: Check ventilation                │
│ • 10:15 - System normal                                  │
└──────────────────────────────────────────────────────────┘
```

**Components**:
1. **Agent Status** (`components/agent_status.py`):
   - WebSocket connection to both agents
   - Show online/offline status
   - Display Agent Card info
   - Connection latency

2. **Sensor Visualization** (`components/sensor_viz.py`):
   - Real-time line charts (Plotly)
   - Last 5 minutes of data
   - Temperature + Humidity chart
   - eCO2 + TVOC chart
   - AQI gauge/indicator (1-5 scale)
   - Anomaly markers on all charts

3. **A2A Conversation** (`components/a2a_conversation.py`):
   - Scrolling message feed
   - Color-coded by agent
   - Expandable JSON for details
   - Auto-scroll to latest

4. **LFM Reasoning** (`components/lfm_reasoning.py`):
   - Token-by-token streaming display
   - Show current thinking process
   - Highlight conclusions
   - Show air quality reasoning (cross-parameter analysis)

**Technical**:
- WebSocket connections to both agents: `ws://jetson-ip:8080/stream`, `ws://macmini-ip:8081/stream`
- Streamlit `st.empty()` for real-time updates
- Auto-refresh every 1 second
- Keep last 100 messages in memory

### 7. Arduino Sensor Code (`arduino/sensor_reader/sensor_reader.ino`)

**Requirements**:
- Read ENS160+AHT21 sensor module via I2C (SDA/SCL)
- Libraries: `ScioSense_ENS160`, `Adafruit_AHTX0`
- Output JSON over serial (9600 baud)
- Format: `{"temp": 24.5, "humidity": 65.2, "eco2": 450, "tvoc": 120, "aqi": 1}`
- Read every 2 seconds
- Handle sensor errors (return null values)
- Note: ENS160 needs ~1 min warm-up, ~1 hour for full calibration

**Example**:
```cpp
#include <Wire.h>
#include <ScioSense_ENS160.h>
#include <Adafruit_AHTX0.h>

ScioSense_ENS160 ens160(ENS160_I2CADDR_1);  // 0x53
Adafruit_AHTX0 aht;

void setup() {
  Serial.begin(9600);
  Wire.begin();

  if (!aht.begin()) {
    Serial.println("{\"error\":\"AHT21 not found\"}");
    while (1) delay(10);
  }

  if (!ens160.begin()) {
    Serial.println("{\"error\":\"ENS160 not found\"}");
    while (1) delay(10);
  }
  ens160.setMode(ENS160_OPMODE_STD);
}

void loop() {
  sensors_event_t humidity_event, temp_event;
  aht.getEvent(&humidity_event, &temp_event);

  float t = temp_event.temperature;
  float h = humidity_event.relative_humidity;

  // Feed AHT21 readings to ENS160 for compensation
  ens160.set_envdata(t, h);
  ens160.measure();

  int eco2 = ens160.geteCO2();
  int tvoc = ens160.getTVOC();
  int aqi  = ens160.getAQI();

  if (isnan(t) || isnan(h)) {
    Serial.println("{\"temp\":null,\"humidity\":null,\"eco2\":null,\"tvoc\":null,\"aqi\":null}");
  } else {
    Serial.print("{\"temp\":");
    Serial.print(t, 1);
    Serial.print(",\"humidity\":");
    Serial.print(h, 1);
    Serial.print(",\"eco2\":");
    Serial.print(eco2);
    Serial.print(",\"tvoc\":");
    Serial.print(tvoc);
    Serial.print(",\"aqi\":");
    Serial.print(aqi);
    Serial.println("}");
  }

  delay(2000);
}
```

## Implementation Priority

**Phase 1: Core Infrastructure**
1. ✅ A2A protocol library (`shared/a2a_protocol.py`)
2. ✅ Agent Card schema (`shared/agent_card.py`)
3. ✅ Storage utilities (`shared/storage.py`)

**Phase 2: Agent Skeletons**
4. ✅ Jetson agent with A2A server (no MCP yet)
5. ✅ Mac Mini agent with A2A server
6. ✅ Test: Agents discover each other, exchange heartbeats

**Phase 3: Sensor Integration**
7. ✅ Arduino code
8. ✅ MCP Arduino Server
9. ✅ Jetson MCP client
10. ✅ Test: Jetson reads sensor, sends observations to Mac Mini

**Phase 4: Intelligence Layer**
11. ✅ LFM client wrapper (`shared/lfm_client.py`)
12. ✅ Jetson anomaly detection with LFM
13. ✅ Mac Mini historical analysis with LFM
14. ✅ Test: Full collaboration loop on anomaly

**Phase 5: Visualization**
15. ✅ Dashboard skeleton
16. ✅ Sensor graphs
17. ✅ A2A message display
18. ✅ LFM reasoning display
19. ✅ Test: Dashboard shows live data from both agents

**Phase 6: Polish**
20. ✅ Error handling throughout
21. ✅ Logging and debugging
22. ✅ Setup scripts
23. ✅ Documentation
24. ✅ Demo script

## Key Implementation Notes

### Error Handling
- All network calls: retry with exponential backoff (max 3 attempts)
- MCP tool calls: timeout after 5 seconds, log failure
- LFM inference: timeout after 30 seconds, return fallback response
- A2A messages: queue locally if peer offline, retry when reconnected

### Logging
- Use Python `logging` module
- JSON Lines format for agent logs
- Include: timestamp, level, component, message, context
- Separate log files per agent

### Configuration
- Environment variables for deployment-specific config (IPs, ports)
- Config files for agent behavior (thresholds, intervals)
- Validation on startup

### Testing
- Unit tests for A2A message serialization
- Integration test: Mock MCP server → Jetson agent
- Integration test: Jetson agent → Mac Mini agent via A2A
- End-to-end test: Full sensor → collaboration → dashboard flow

## Success Criteria

**Functional**:
- [ ] Arduino sends sensor data every 2 seconds
- [ ] MCP server exposes data as tool
- [ ] Jetson agent reads sensor every 5 seconds via MCP
- [ ] Jetson sends observations to Mac Mini via A2A
- [ ] Agents detect anomalies (temp delta >5°C, eCO2 >1000ppm, TVOC >500ppb, AQI >=4)
- [ ] LFM analysis runs on both agents
- [ ] Collaborative decision logged by both agents
- [ ] Dashboard displays all activity in real-time
- [ ] System handles agent restart gracefully

**Performance**:
- [ ] A2A message round-trip < 2 seconds
- [ ] LFM inference < 10 seconds
- [ ] Dashboard updates < 500ms lag
- [ ] No memory leaks over 1 hour operation

**Demo Ready**:
- [ ] Clear README with setup instructions
- [ ] Demo script with talking points
- [ ] All components start with single command
- [ ] Visually compelling dashboard
- [ ] Handles anomaly scenario smoothly

## Questions for Implementation

1. **HuggingFace Model ID**: What's the exact model ID for Liquid AI LFM 2.5 1.2B on HuggingFace?
   - Search HuggingFace if uncertain, or use placeholder and document for later

2. **Network Configuration**: 
   - Should agents discover each other automatically (mDNS) or use static IPs in config?
   - Recommendation: Static IPs for demo simplicity, document in config files

3. **Dashboard Hosting**:
   - Run on Mac Mini (same machine as agent)?
   - Recommendation: Yes, simplest for demo

4. **LFM Prompts**:
   - Create effective prompts for anomaly detection and analysis?
   - Recommendation: Start simple, iterate based on outputs

5. **Data Retention**:
   - How long to keep sensor data logs?
   - Recommendation: Last 24 hours in memory, longer in files

## Deliverables

1. **Complete codebase** matching structure above
2. **README.md** with:
   - Architecture diagram
   - Setup instructions for Jetson
   - Setup instructions for Mac Mini
   - Arduino setup
   - Running the demo
   - Troubleshooting
3. **DEMO_SCRIPT.md** with:
   - Demo narrative
   - Step-by-step actions
   - Expected outcomes
   - Talking points for AI Futures Lab
4. **Requirements.txt files** for each component
5. **Setup scripts** for automated deployment
6. **Basic tests** to validate functionality

## Additional Context

- This is for a **live demo**, so reliability > features
- Audience is **technical** (AI researchers/engineers)
- Focus on **thought leadership**: "This is how edge AI should work"
- Emphasize **interoperability**: MCP and A2A as standards
- Show **visible reasoning**: LFM thinking process is key differentiator
- Keep it **simple**: Two agents, one sensor, clear collaboration story

---

## Request to Claude Code

Please implement this Agent Edge system following the architecture and requirements above. Start with Phase 1 (core infrastructure), then build up through the phases. Ask clarifying questions if any requirements are ambiguous. Prioritize working code over perfect code - we can iterate. The goal is a functional demo that shows edge AI thought leadership.

Begin with setting up the project structure and implementing the shared A2A protocol library.
