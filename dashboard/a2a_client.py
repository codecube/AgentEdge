"""Synchronous A2A client for Streamlit dashboard.

Uses httpx sync client to POST JSON-RPC ``message/send`` requests.
This avoids async/Streamlit mismatch issues.
"""
from __future__ import annotations

import uuid

import httpx


def send_a2a_message(agent_url: str, text: str, timeout: float = 30.0) -> dict:
    """Send a text message to an A2A agent and return the response.

    Args:
        agent_url: Base URL of the A2A agent (e.g. ``http://localhost:8081``).
        text: The user message text.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON-RPC response dict.  On error, returns a dict with
        an ``error`` key.
    """
    message_id = uuid.uuid4().hex
    request_id = str(uuid.uuid4())

    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "message/send",
        "params": {
            "message": {
                "role": "user",
                "parts": [{"kind": "text", "text": text}],
                "messageId": message_id,
            }
        },
    }

    try:
        resp = httpx.post(agent_url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except httpx.ConnectError:
        return {"error": "Agent is not reachable."}
    except httpx.TimeoutException:
        return {"error": "Request timed out — the agent may be busy."}
    except Exception as e:
        return {"error": str(e)}


def extract_agent_reply(response: dict) -> str:
    """Extract the agent's text reply from a JSON-RPC response.

    Handles both ``result.message.parts`` (direct response) and
    ``result.status.message.parts`` (task-based response).
    """
    if "error" in response:
        return response["error"]

    result = response.get("result", {})

    # Direct message response
    message = result.get("message")
    if not message:
        # Task-based response
        message = (result.get("status") or {}).get("message")
    if not message:
        return "No response from agent."

    parts = message.get("parts", [])
    texts = []
    for part in parts:
        if part.get("kind") == "text" or part.get("type") == "text":
            texts.append(part.get("text", ""))
    return "\n".join(texts) if texts else "No text in response."


def fetch_agent_card(agent_url: str) -> dict | None:
    """Fetch the A2A agent card from /.well-known/agent-card.json.

    Returns None if the agent is unreachable.
    """
    try:
        resp = httpx.get(
            f"{agent_url}/.well-known/agent-card.json", timeout=3.0
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None
