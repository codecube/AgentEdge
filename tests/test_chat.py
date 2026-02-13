"""Tests for chat feature — REST /api/chat and data-only answer helper."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from agents.macmini.dashboard_routes import _data_only_answer, router as dashboard_router
from shared import state


def _make_test_app() -> FastAPI:
    """Build a minimal FastAPI app with dashboard routes for testing."""
    app = FastAPI()
    app.include_router(dashboard_router, prefix="/api")
    return app


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

    def test_humidity_question(self, current, stats):
        result = _data_only_answer("What's the humidity?", current, stats)
        assert "65.2%" in result

    def test_temperature_question(self, current, stats):
        result = _data_only_answer("What is the temperature?", current, stats)
        assert "24.5" in result

    def test_eco2_question(self, current, stats):
        result = _data_only_answer("How is the CO2 level?", current, stats)
        assert "450" in result

    def test_general_question(self, current, stats):
        result = _data_only_answer("Give me a summary", current, stats)
        assert "24.5" in result
        assert "65.2" in result

    def test_no_data(self):
        result = _data_only_answer("What's happening?", None, {})
        assert "No sensor data" in result

    def test_stats_only_fallback(self):
        stats = {
            "temperature": {"mean": 23.0, "stdev": 1.5, "min": 20.0, "max": 27.0, "count": 50},
        }
        result = _data_only_answer("What's the temp?", None, stats)
        assert "Historical" in result


# --- /api/chat endpoint ---


class TestChatEndpoint:
    @pytest.fixture()
    def client(self):
        return TestClient(_make_test_app())

    def test_chat_returns_answer(self, client):
        state.sensor_history.clear()
        state.sensor_history.append({
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


# --- Aggregation endpoints ---


class TestAggregationEndpoints:
    @pytest.fixture()
    def client(self):
        return TestClient(_make_test_app())

    def test_agents_endpoint(self, client):
        resp = client.get("/api/agents")
        assert resp.status_code == 200
        body = resp.json()
        assert "jetson" in body
        assert "macmini" in body
        assert body["macmini"] is not None

    def test_messages_endpoint(self, client):
        resp = client.get("/api/messages?limit=10")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_reasoning_endpoint(self, client):
        resp = client.get("/api/reasoning")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_chat_populates_messages(self, client):
        state.sensor_history.clear()
        state.sensor_history.append({
            "temperature": 22.0,
            "humidity": 55.0,
            "eco2": 400,
            "tvoc": 100,
            "aqi": 1,
        })
        state.a2a_messages.clear()

        client.post("/api/chat", json={"question": "temperature?"})

        resp = client.get("/api/messages")
        msgs = resp.json()
        types = [m["event"] for m in msgs]
        assert "query" in types
        assert "query_response" in types
