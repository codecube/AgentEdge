"""Synchronous A2A client for Streamlit dashboard.

Uses httpx sync client to POST JSON-RPC ``message/send`` requests.
This avoids async/Streamlit mismatch issues.
"""
from __future__ import annotations

import json
import logging
import uuid

import httpx

logger = logging.getLogger(__name__)


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

    Searches every possible location where agent text can appear in
    ADK / A2A responses.
    """
    if "error" in response:
        return response["error"]

    result = response.get("result", {})

    # Try each location in priority order, return first match.

    # 1. History messages (most common ADK format)
    for msg in reversed(result.get("history", [])):
        if msg.get("role") == "agent":
            found = _extract_text_parts(msg.get("parts", []))
            if found:
                return "\n".join(found)

    # 2. Artifacts
    for artifact in result.get("artifacts", []):
        found = _extract_text_parts(artifact.get("parts", []))
        if found:
            return "\n".join(found)

    # 3. Result is itself a direct message
    if result.get("role") == "agent" and result.get("parts"):
        found = _extract_text_parts(result["parts"])
        if found:
            return "\n".join(found)

    # 4. Nested message field
    message = result.get("message")
    if not message:
        message = (result.get("status") or {}).get("message")
    if message:
        found = _extract_text_parts(message.get("parts", []))
        if found:
            return "\n".join(found)

    # Last resort: dump the full response for debugging
    logger.warning(
        "Could not extract agent reply. Full response:\n%s",
        json.dumps(response, indent=2, default=str)[:2000],
    )
    return "No response from agent."


def _extract_text_parts(parts: list) -> list[str]:
    """Pull text strings from a list of A2A message parts.

    Skips internal thinking tokens (``adk_thought``) so only the
    agent's actual reply is returned.
    """
    texts = []
    for part in parts:
        # Skip ADK internal thinking tokens
        meta = part.get("metadata") or {}
        if meta.get("adk_thought"):
            continue
        if part.get("kind") == "text" or part.get("type") == "text":
            text = part.get("text", "").strip()
            if text:
                texts.append(text)
    return texts


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
