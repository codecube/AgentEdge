"""Interactive CLI chat for the Jetson agent — talk to LFM and read live sensors."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

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
BANNER = rf"""
{CYAN}{BOLD}
        ██╗
       ████╗        ╔═╗ ╔═╗ ╔══╗ ╔═╗ ╗ ╔╗ ╔══╗
      ██  ██        ║ ║ ║ ╔╝ ║╔═╝ ║ ╚╗║║ ╚╗╔╝
     ██    ██       ╠═╣ ║ ╚╗ ║╚═  ║  ╚╝║  ║║
    ██  ██  ██      ║ ║ ╚═╝ ╚══╝ ╝   ╚╝  ╚╝
    ██ ████ ██
    ████████████    {AMBER}╔══╗ ╔══╗ ╔══╗ ╔══╗
     ██████████     ║╔═╝ ║ ╠╝ ║ ╔╝ ║╔═╝
      ████████      ║╚═  ║ ╚╗ ╚═║  ║╚═
       ██████       ╚══╝ ╚══╝ ╚══╝ ╚══╝{CYAN}
        ████
         ██         {DIM}Jetson Edge Intelligence CLI{RESET}
{RESET}"""

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


def _check(ok: bool) -> str:
    return f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"


def _format_sensor(data: dict) -> str:
    """Pretty-print a sensor reading."""
    lines = [
        f"  {BOLD}Temperature{RESET}  {data.get('temp', '?')} °C",
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


async def _read_sensor(mcp) -> dict | None:
    """Safely read sensor data via MCP."""
    if mcp is None:
        return None
    try:
        return await mcp.read_sensor()
    except Exception as e:
        logger.warning("Sensor read failed: %s", e)
        return None


async def main() -> None:
    print(BANNER)

    # ── Initialise LFM ───────────────────────────────────────────────────
    lfm = None
    try:
        from shared.lfm_client import LFMClient
        print(f"  {DIM}Loading LFM model ({config.LFM_MODEL})…{RESET}", end="", flush=True)
        lfm = LFMClient(config.LFM_MODEL)
        print(f"\r  LFM model       {_check(True)}  {DIM}{config.LFM_MODEL}{RESET}")
    except Exception as e:
        print(f"\r  LFM model       {_check(False)}  {DIM}{e}{RESET}")

    # ── Initialise MCP ───────────────────────────────────────────────────
    mcp = None
    mcp_cm = None
    try:
        from agents.jetson.mcp_client import MCPArduinoClient
        mcp_cm = MCPArduinoClient(config.SERIAL_PORT, config.SERIAL_BAUD)
        mcp = await mcp_cm.__aenter__()
        # Test read to verify connection
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
                data = await _read_sensor(mcp)
                if data:
                    last_sensor = data
                    print(f"\n{CYAN}Sensor Reading:{RESET}")
                    print(_format_sensor(data))
                else:
                    print(f"\n{RED}Sensor unavailable.{RESET} Is the Arduino connected?")
                print()
                continue

            if cmd == "/status":
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
            if lfm is None:
                print(f"\n{RED}LFM not available.{RESET} Only /sensor commands work.\n")
                continue

            # Auto-fetch latest sensor data for context
            sensor_ctx = await _read_sensor(mcp)
            if sensor_ctx:
                last_sensor = sensor_ctx

            prompt = _build_prompt(text, sensor_ctx or last_sensor)

            # Stream response
            print(f"\n{CYAN}", end="", flush=True)
            try:
                async for token in lfm.analyze_streaming(prompt):
                    print(token, end="", flush=True)
            except Exception as e:
                print(f"{RESET}\n{RED}LFM error: {e}{RESET}")
            print(f"{RESET}\n")

    finally:
        # Clean up MCP connection
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
