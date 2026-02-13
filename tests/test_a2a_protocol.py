"""Tests for A2A protocol integration — message format, client, agent cards."""
from __future__ import annotations

import uuid

import pytest

from dashboard.a2a_client import extract_agent_reply, send_a2a_message


class TestA2AMessageFormat:
    """Verify JSON-RPC message/send payload structure."""

    def test_message_payload_shape(self):
        message_id = uuid.uuid4().hex
        request_id = str(uuid.uuid4())

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "test question"}],
                    "messageId": message_id,
                }
            },
        }

        assert payload["jsonrpc"] == "2.0"
        assert payload["method"] == "message/send"
        msg = payload["params"]["message"]
        assert msg["role"] == "user"
        assert len(msg["parts"]) == 1
        assert msg["parts"][0]["kind"] == "text"
        assert msg["parts"][0]["text"] == "test question"


class TestExtractAgentReply:
    def test_direct_message_response(self):
        response = {
            "result": {
                "message": {
                    "role": "agent",
                    "parts": [{"kind": "text", "text": "Temperature is 24.5C"}],
                    "messageId": "abc123",
                }
            }
        }
        assert extract_agent_reply(response) == "Temperature is 24.5C"

    def test_task_based_response(self):
        response = {
            "result": {
                "status": {
                    "message": {
                        "role": "agent",
                        "parts": [{"kind": "text", "text": "AQI is 2/5"}],
                        "messageId": "def456",
                    }
                }
            }
        }
        assert extract_agent_reply(response) == "AQI is 2/5"

    def test_error_response(self):
        response = {"error": "Agent is not reachable."}
        assert extract_agent_reply(response) == "Agent is not reachable."

    def test_empty_result(self):
        response = {"result": {}}
        assert extract_agent_reply(response) == "No response from agent."

    def test_multiple_parts(self):
        response = {
            "result": {
                "message": {
                    "role": "agent",
                    "parts": [
                        {"kind": "text", "text": "Part 1"},
                        {"kind": "text", "text": "Part 2"},
                    ],
                    "messageId": "multi",
                }
            }
        }
        assert extract_agent_reply(response) == "Part 1\nPart 2"

    def test_type_variant(self):
        """Some SDKs use 'type' instead of 'kind'."""
        response = {
            "result": {
                "message": {
                    "role": "agent",
                    "parts": [{"type": "text", "text": "Fallback"}],
                    "messageId": "compat",
                }
            }
        }
        assert extract_agent_reply(response) == "Fallback"


class TestSendA2AMessageUnreachable:
    def test_unreachable_returns_error(self):
        result = send_a2a_message("http://localhost:19999", "test", timeout=1.0)
        assert "error" in result
