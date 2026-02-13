"""Interactive CLI chat for the Jetson agent — talk to LFM and read live sensors."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

import httpx

from agents.jetson import config

# ── ANSI colours ──────────────────────────────────────────────────────────────
CYAN = "\033[96m"
AMBER = "\033[93m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
GREEN = "\033[92m"
RED = "\033[91m"

# ── ASCII banner ──────────────────────────────────────────────────────────────
BANNER = f"""
{CYAN}{BOLD}     _                    _   _____    _
    / \\   __ _  ___ _ __ | |_| ____|__| | __ _  ___
   / _ \\ / _` |/ _ \\ '_ \\| __|  _| / _` |/ _` |/ _ \\
  / ___ \\ (_| |  __/ | | | |_| |__| (_| | (_| |  __/
 /_/   \\_\\__, |\\___|_| |_|\\__|_____\\__,_|\\__, |\\___|
         |___/                            |___/{RESET}
{AMBER}         Capgemini AI Futures Lab{RESET}
"""

HELP_TEXT = f"""{BOLD}Commands:{RESET}
  {AMBER}/sensor{RESET}, {AMBER}/read{RESET}   Read live sensor data
  {AMBER}/status{RESET}         Show connection status
  {AMBER}/clear{RESET}          Clear the terminal
  {AMBER}/help{RESET}           Show this help
  {AMBER}/quit{RESET}, {AMBER}/exit{RESET}    Exit the CLI

  {DIM}Or type any question to chat with LFM.{RESET}
"""

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

AGENT_BASE_URL = f"http://localhost:{config.AGENT_PORT}"


def _check(ok: bool) -> str:
    return f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"


def _format_sensor(data: dict) -> str:
    """Pretty-print a sensor reading."""
    lines = [
        f"  {BOLD}Temperature{RESET}  {data.get('temp', data.get('temperature', '?'))} °C",
        f"  {BOLD}Humidity{RESET}     {data.get('humidity', '?')} %",
        f"  {BOLD}eCO2{RESET}         {data.get('eco2', '?')} ppm",
        f"  {BOLD}TVOC{RESET}         {data.get('tvoc', '?')} ppb",
        f"  {BOLD}AQI{RESET}          {data.get('aqi', '?')} / 5",
    ]
    return "\n".join(lines)


def _build_prompt(question: str, sensor_data: dict | None) -> str:
    """Build an LFM prompt with optional sensor context."""
    if sensor_data:
        sensor_block = (
            f"- Temperature: {sensor_data.get('temp')}°C\n"
            f"- Humidity: {sensor_data.get('humidity')}%\n"
            f"- eCO2: {sensor_data.get('eco2')} ppm\n"
            f"- TVOC: {sensor_data.get('tvoc')} ppb\n"
            f"- AQI: {sensor_data.get('aqi')}/5"
        )
    else:
        sensor_block = "- No live sensor data available"

    return (
        "You are an AI assistant for the Agent Edge environmental monitoring system "
        f"at {config.LOCATION}.\n"
        "You have access to live sensor data from an ENS160+AHT21 module.\n\n"
        f"Current sensor data:\n{sensor_block}\n\n"
        f"User question: {question}\n\n"
        "Provide a concise, helpful answer."
    )


async def _read_sensor_mcp(mcp) -> dict | None:
    """Safely read sensor data via MCP."""
    if mcp is None:
        return None
    try:
        return await mcp.read_sensor()
    except Exception as e:
        logger.warning("Sensor read failed: %s", e)
        return None


async def _read_sensor_http(client: httpx.AsyncClient) -> dict | None:
    """Read sensor data via the agent HTTP API."""
    try:
        resp = await client.get(f"{AGENT_BASE_URL}/api/sensor/current")
        data = resp.json()
        if data.get("status") == "ok" and data.get("reading"):
            return data["reading"]
        return None
    except Exception as e:
        logger.warning("Agent sensor read failed: %s", e)
        return None


async def _stream_chat_http(client: httpx.AsyncClient, question: str) -> None:
    """Stream a chat response from the agent's SSE endpoint."""
    print(f"\n{CYAN}", end="", flush=True)
    try:
        async with client.stream(
            "POST",
            f"{AGENT_BASE_URL}/api/chat/stream",
            json={"question": question},
            timeout=120.0,
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("event: done"):
                    break
                if line.startswith("event: error"):
                    continue
                if line.startswith("data: "):
                    token = json.loads(line[6:])
                    print(token, end="", flush=True)
    except Exception as e:
        print(f"{RESET}\n{RED}Agent stream error: {e}{RESET}")
    print(f"{RESET}\n")


async def _check_agent() -> bool:
    """Check if the Jetson agent is running."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{AGENT_BASE_URL}/health")
            return resp.status_code == 200
    except Exception:
        return False


async def main() -> None:
    print(BANNER)

    # ── Check if agent is running ─────────────────────────────────────────
    agent_url: str | None = None
    http_client: httpx.AsyncClient | None = None
    lfm = None
    mcp = None
    mcp_cm = None

    agent_available = await _check_agent()

    if agent_available:
        agent_url = AGENT_BASE_URL
        http_client = httpx.AsyncClient(timeout=10.0)
        print(f"  LFM (via agent) {_check(True)}  {DIM}{agent_url}{RESET}")
        print(f"  Sensor (agent)  {_check(True)}  {DIM}{agent_url}/api/sensor/current{RESET}")
    else:
        # ── Fallback: load LFM locally ────────────────────────────────────
        try:
            from shared.lfm_client import LFMClient

            print(f"  {DIM}Loading LFM model ({config.LFM_MODEL})…{RESET}", end="", flush=True)
            lfm = LFMClient(config.LFM_MODEL)
            print(f"\r  LFM model       {_check(True)}  {DIM}{config.LFM_MODEL}{RESET}")
        except Exception as e:
            print(f"\r  LFM model       {_check(False)}  {DIM}{e}{RESET}")

        # ── Fallback: init MCP directly ───────────────────────────────────
        try:
            from agents.jetson.mcp_client import MCPArduinoClient

            mcp_cm = MCPArduinoClient(config.SERIAL_PORT, config.SERIAL_BAUD)
            mcp = await mcp_cm.__aenter__()
            test = await mcp.read_sensor()
            if test is not None:
                print(f"  Sensor (MCP)    {_check(True)}  {DIM}{config.SERIAL_PORT}{RESET}")
            else:
                print(f"  Sensor (MCP)    {_check(False)}  {DIM}connected but no data{RESET}")
        except Exception as e:
            print(f"  Sensor (MCP)    {_check(False)}  {DIM}{e}{RESET}")
            mcp = None
            mcp_cm = None

    print()
    print(f"  {DIM}Type /help for commands or ask a question.{RESET}")
    print()

    loop = asyncio.get_event_loop()
    last_sensor: dict | None = None

    try:
        while True:
            # Read input via executor to avoid blocking the event loop
            try:
                line = await loop.run_in_executor(
                    None, lambda: input(f"{AMBER}agent-edge ❯{RESET} ")
                )
            except EOFError:
                break

            text = line.strip()
            if not text:
                continue

            # ── Commands ──────────────────────────────────────────────
            cmd = text.lower()

            if cmd in ("/quit", "/exit"):
                print(f"\n{DIM}Goodbye.{RESET}")
                break

            if cmd in ("/sensor", "/read"):
                data = None
                if http_client:
                    data = await _read_sensor_http(http_client)
                else:
                    data = await _read_sensor_mcp(mcp)
                if data:
                    last_sensor = data
                    print(f"\n{CYAN}Sensor Reading:{RESET}")
                    print(_format_sensor(data))
                else:
                    print(f"\n{RED}Sensor unavailable.{RESET} Is the Arduino connected?")
                print()
                continue

            if cmd == "/status":
                if agent_url:
                    print(f"\n  LFM (via agent) {_check(True)}")
                    print(f"  Sensor (agent)  {_check(True)}")
                else:
                    print(f"\n  LFM model       {_check(lfm is not None)}")
                    print(f"  Sensor (MCP)    {_check(mcp is not None)}")
                print(f"  Location        {DIM}{config.LOCATION}{RESET}")
                if last_sensor:
                    print(f"  Last reading    {DIM}{json.dumps(last_sensor)}{RESET}")
                print()
                continue

            if cmd == "/clear":
                os.system("clear" if os.name != "nt" else "cls")
                continue

            if cmd == "/help":
                print()
                print(HELP_TEXT)
                continue

            if cmd.startswith("/"):
                print(f"{RED}Unknown command:{RESET} {text}. Type /help for commands.")
                continue

            # ── Chat with LFM ────────────────────────────────────────
            if http_client:
                await _stream_chat_http(http_client, text)
                continue

            if lfm is None:
                print(f"\n{RED}LFM not available.{RESET} Only /sensor commands work.\n")
                continue

            # Local LFM fallback
            sensor_ctx = await _read_sensor_mcp(mcp)
            if sensor_ctx:
                last_sensor = sensor_ctx

            prompt = _build_prompt(text, sensor_ctx or last_sensor)

            print(f"\n{CYAN}", end="", flush=True)
            try:
                async for token in lfm.analyze_streaming(prompt):
                    print(token, end="", flush=True)
            except Exception as e:
                print(f"{RESET}\n{RED}LFM error: {e}{RESET}")
            print(f"{RESET}\n")

    finally:
        if http_client:
            await http_client.aclose()
        if mcp_cm is not None:
            try:
                await mcp_cm.__aexit__(None, None, None)
            except Exception:
                pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{DIM}Interrupted.{RESET}")
