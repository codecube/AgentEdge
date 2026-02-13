"""Tests for chat feature — QUERY/QUERY_RESPONSE messages and chat helpers."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from shared.a2a_protocol import (
    MessageType,
    Query,
    QueryPayload,
    QueryResponse,
    QueryResponsePayload,
    parse_message,
)


# --- A2A message types ---


class TestQueryMessage:
    def test_create(self):
        msg = Query(
            **{"from": "macmini-control"},
            to="jetson-site-a",
            payload=QueryPayload(
                question="What is the current humidity?",
                source="dashboard",
            ),
        )
        assert msg.type == MessageType.QUERY
        assert msg.payload.question == "What is the current humidity?"
        assert msg.payload.source == "dashboard"

    def test_serialization_roundtrip(self):
        msg = Query(
            **{"from": "macmini-control"},
            to="jetson-site-a",
            payload=QueryPayload(
                question="What is the temperature?",
                source="dashboard",
                context={"session": "test"},
            ),
        )
        data = msg.model_dump(by_alias=True)
        assert data["type"] == "query"
        assert data["from"] == "macmini-control"
        assert data["payload"]["question"] == "What is the temperature?"

        parsed = parse_message(data)
        assert isinstance(parsed, Query)
        assert parsed.payload.question == "What is the temperature?"


class TestQueryResponseMessage:
    def test_create(self):
        msg = QueryResponse(
            **{"from": "jetson-site-a"},
            to="macmini-control",
            in_reply_to="msg-123",
            payload=QueryResponsePayload(
                answer="Current humidity is 65%",
                data={"humidity": 65.0},
                source_agent="jetson-site-a",
            ),
        )
        assert msg.type == MessageType.QUERY_RESPONSE
        assert msg.in_reply_to == "msg-123"
        assert msg.payload.answer == "Current humidity is 65%"

    def test_serialization_roundtrip(self):
        msg = QueryResponse(
            **{"from": "jetson-site-a"},
            to="macmini-control",
            in_reply_to="msg-456",
            payload=QueryResponsePayload(
                answer="Temperature is 24.5C",
                data={"temperature": 24.5},
                source_agent="jetson-site-a",
            ),
        )
        data = msg.model_dump(by_alias=True)
        assert data["type"] == "query_response"
        assert data["payload"]["source_agent"] == "jetson-site-a"

        parsed = parse_message(data)
        assert isinstance(parsed, QueryResponse)
        assert parsed.payload.data["temperature"] == 24.5


# --- Data-only answer helper ---


class TestDataOnlyAnswer:
    @pytest.fixture()
    def current(self):
        return {
            "temperature": 24.5,
            "humidity": 65.2,
            "eco2": 450,
            "tvoc": 120,
            "aqi": 1,
        }

    @pytest.fixture()
    def stats(self):
        return {
            "temperature": {"mean": 23.0, "stdev": 1.5, "min": 20.0, "max": 27.0, "count": 50},
            "humidity": {"mean": 60.0, "stdev": 5.0, "min": 50.0, "max": 75.0, "count": 50},
        }

    def _answer(self, question, current, stats):
        from agents.macmini.agent import _data_only_answer

        return _data_only_answer(question, current, stats)

    def test_humidity_question(self, current, stats):
        result = self._answer("What's the humidity?", current, stats)
        assert "65.2%" in result

    def test_temperature_question(self, current, stats):
        result = self._answer("What is the temperature?", current, stats)
        assert "24.5" in result

    def test_eco2_question(self, current, stats):
        result = self._answer("How is the CO2 level?", current, stats)
        assert "450" in result

    def test_general_question(self, current, stats):
        result = self._answer("Give me a summary", current, stats)
        assert "24.5" in result
        assert "65.2" in result

    def test_no_data(self):
        result = self._answer("What's happening?", None, {})
        assert "No sensor data" in result

    def test_stats_only_fallback(self):
        stats = {
            "temperature": {"mean": 23.0, "stdev": 1.5, "min": 20.0, "max": 27.0, "count": 50},
        }
        result = self._answer("What's the temp?", None, stats)
        assert "Historical" in result


# --- /api/chat endpoint ---


class TestChatEndpoint:
    @pytest.fixture()
    def client(self):
        """Create a test client for the Mac Mini agent."""
        from agents.macmini.agent import app

        return TestClient(app)

    def test_chat_returns_answer(self, client, monkeypatch):
        # Seed sensor_history so it has data to answer from
        from agents.macmini import agent as mac_agent

        mac_agent.sensor_history.clear()
        mac_agent.sensor_history.append({
            "temperature": 24.5,
            "humidity": 65.2,
            "eco2": 450,
            "tvoc": 120,
            "aqi": 1,
        })

        resp = client.post("/api/chat", json={"question": "What is the humidity?"})
        assert resp.status_code == 200
        body = resp.json()
        assert "answer" in body
        assert "data_used" in body
        assert "65.2" in body["answer"]

    def test_chat_empty_question(self, client):
        resp = client.post("/api/chat", json={"question": "   "})
        assert resp.status_code == 200
        assert "Please ask" in resp.json()["answer"]
