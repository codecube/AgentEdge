"""Module-level shared state for agent processes.

Each agent process imports this module and gets its own copy of the state
(Python modules are per-process). Tools and dashboard routes import from
here to avoid circular dependencies.
"""
from __future__ import annotations

from typing import Any

# --- Jetson state ---
previous_reading: dict | None = None

# --- Mac Mini state ---
sensor_history: list[dict] = []
a2a_messages: list[dict] = []
reasoning_events: list[dict] = []

# --- Common state ---
peer_card: dict | None = None
peer_last_seen: float = 0.0
ws_clients: list[Any] = []  # list[WebSocket], untyped to avoid import

MAX_A2A_MESSAGES = 100
MAX_REASONING_EVENTS = 20
SENSOR_FIELDS = ["temperature", "humidity", "eco2", "tvoc", "aqi"]


async def broadcast_ws(data: dict) -> None:
    """Broadcast JSON data to all connected WebSocket clients."""
    import json

    msg = json.dumps(data)
    disconnected = []
    for ws in ws_clients:
        try:
            await ws.send_text(msg)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        ws_clients.remove(ws)


def record_a2a_message(event: str, data: dict) -> None:
    """Append to the in-memory A2A message list (capped)."""
    a2a_messages.append({"event": event, "data": data})
    if len(a2a_messages) > MAX_A2A_MESSAGES:
        a2a_messages[:] = a2a_messages[-MAX_A2A_MESSAGES:]


def record_reasoning_event(event: dict) -> None:
    """Append to the in-memory reasoning events list (capped)."""
    reasoning_events.append(event)
    if len(reasoning_events) > MAX_REASONING_EVENTS:
        reasoning_events[:] = reasoning_events[-MAX_REASONING_EVENTS:]
