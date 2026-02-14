"""Interactive CLI chat for the Jetson agent — talk to LFM and read live sensors.

Requires the Jetson agent server to be running (python3 -m agents.jetson.server).
Connects via the agent's HTTP API for both sensor reads and chat.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os

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
{CYAN}         Capgemini AI Futures Lab{RESET}
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


async def _chat_a2a(client: httpx.AsyncClient, question: str) -> None:
    """Send a chat question via A2A message/stream and print tokens as they arrive."""
    import uuid

    message_id = uuid.uuid4().hex
    request_id = str(uuid.uuid4())

    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "message/stream",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": question}],
                "messageId": message_id,
            }
        },
    }

    print()
    collected = ""
    try:
        async with client.stream(
            "POST", AGENT_BASE_URL, json=payload, timeout=120.0
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data_str = line[len("data:"):].strip()
                if not data_str:
                    continue
                try:
                    event = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                text = _extract_event_text(event)
                if text and len(text) > len(collected):
                    new_chars = text[len(collected):]
                    print(f"{CYAN}{new_chars}{RESET}", end="", flush=True)
                    collected = text

        if not collected:
            print(f"{RED}No response from agent.{RESET}", end="")
        print("\n")
    except httpx.ConnectError:
        print(f"{RED}Agent is not reachable.{RESET}\n")
    except httpx.TimeoutException:
        print(f"{RED}Request timed out — the agent may be busy.{RESET}\n")
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}\n")


def _extract_event_text(event: dict) -> str | None:
    """Extract agent text from an A2A SSE event.

    Handles multiple event shapes:
    - artifact-update with parts
    - status-update with message
    - final result with history
    - direct message result
    """
    result = event.get("result", event)

    # Artifact update — streaming text chunks
    artifact = result.get("artifact")
    if artifact:
        text = _text_from_parts(artifact.get("parts", []))
        if text:
            return text

    # Status update with message
    status = result.get("status") or {}
    message = status.get("message")
    if message:
        text = _text_from_parts(message.get("parts", []))
        if text:
            return text

    # Final result with history
    for msg in reversed(result.get("history", [])):
        if msg.get("role") == "agent":
            text = _text_from_parts(msg.get("parts", []))
            if text:
                return text

    # Direct message result
    if result.get("role") == "agent":
        text = _text_from_parts(result.get("parts", []))
        if text:
            return text

    return None


def _text_from_parts(parts: list) -> str | None:
    """Join non-thought text parts."""
    texts = []
    for part in parts:
        meta = part.get("metadata") or {}
        if meta.get("adk_thought"):
            continue
        if part.get("kind") == "text" and part.get("text", "").strip():
            texts.append(part["text"])
    return "\n".join(texts) if texts else None


async def _check_agent() -> bool:
    """Check if the Jetson agent server is reachable."""
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{AGENT_BASE_URL}/api/sensor/current")
            return resp.status_code == 200
    except Exception:
        return False


async def main() -> None:
    print(BANNER)

    # ── Check if agent server is running ──────────────────────────────────
    agent_available = await _check_agent()

    if not agent_available:
        print(f"  Agent server    {_check(False)}  {DIM}{AGENT_BASE_URL}{RESET}")
        print()
        print(f"  {RED}The Jetson agent server must be running.{RESET}")
        print(f"  {DIM}Start it with: python3 -m agents.jetson.server{RESET}")
        return

    http_client = httpx.AsyncClient(timeout=10.0)
    print(f"  Agent server    {_check(True)}  {DIM}{AGENT_BASE_URL}{RESET}")
    print(f"  Sensor (agent)  {_check(True)}  {DIM}{AGENT_BASE_URL}/api/sensor/current{RESET}")

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
                data = await _read_sensor_http(http_client)
                if data:
                    last_sensor = data
                    print(f"\n{CYAN}Sensor Reading:{RESET}")
                    print(_format_sensor(data))
                else:
                    print(f"\n{RED}Sensor unavailable.{RESET} Is the Arduino connected?")
                print()
                continue

            if cmd == "/status":
                print(f"\n  Agent server    {_check(True)}")
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

            # ── Chat via A2A message/stream ────────────────────────────
            await _chat_a2a(http_client, text)

    finally:
        await http_client.aclose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{DIM}Interrupted.{RESET}")
