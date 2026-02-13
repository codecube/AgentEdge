"""Tests for A2A protocol message serialization and validation."""

import pytest

from shared.a2a_protocol import (
    AgentCardPayload,
    AgentEndpoints,
    AgentStatus,
    AnalysisRequest,
    AnalysisRequestPayload,
    AnalysisResponse,
    AnalysisResponsePayload,
    Decision,
    DecisionPayload,
    Heartbeat,
    MessageType,
    SensorObservation,
    SensorPayload,
    parse_message,
)


class TestSensorObservation:
    def test_create_with_all_fields(self):
        obs = SensorObservation(
            **{"from": "jetson-site-a"},
            to="macmini-control",
            payload=SensorPayload(
                temperature=24.5,
                humidity=65.2,
                eco2=450,
                tvoc=120,
                aqi=1,
                location="Site A",
            ),
        )
        assert obs.type == MessageType.SENSOR_OBSERVATION
        assert obs.payload.temperature == 24.5
        assert obs.payload.humidity == 65.2
        assert obs.payload.eco2 == 450
        assert obs.payload.tvoc == 120
        assert obs.payload.aqi == 1
        assert obs.payload.sensor == "ENS160+AHT21"

    def test_serialization_roundtrip(self):
        obs = SensorObservation(
            **{"from": "jetson-site-a"},
            to="macmini-control",
            payload=SensorPayload(
                temperature=24.5,
                humidity=65.2,
                eco2=450,
                tvoc=120,
                aqi=1,
                location="Site A",
            ),
        )
        data = obs.model_dump(by_alias=True)
        assert data["type"] == "sensor_observation"
        assert data["from"] == "jetson-site-a"
        assert data["payload"]["eco2"] == 450
        assert "message_id" in data
        assert "timestamp" in data

    def test_parse_from_dict(self):
        data = {
            "type": "sensor_observation",
            "from": "jetson-site-a",
            "to": "macmini-control",
            "message_id": "test-123",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "payload": {
                "sensor": "ENS160+AHT21",
                "temperature": 24.5,
                "humidity": 65.2,
                "eco2": 450,
                "tvoc": 120,
                "aqi": 1,
                "location": "Site A",
            },
        }
        msg = parse_message(data)
        assert isinstance(msg, SensorObservation)
        assert msg.payload.eco2 == 450


class TestAnalysisRequest:
    def test_create(self):
        req = AnalysisRequest(
            **{"from": "jetson-site-a"},
            to="macmini-control",
            payload=AnalysisRequestPayload(
                question="Is eCO2 1200ppm anomalous?",
                context={"eco2": 1200, "temperature": 23.0},
                lfm_thinking="CO2 spike detected...",
            ),
        )
        assert req.type == MessageType.ANALYSIS_REQUEST
        assert req.payload.question == "Is eCO2 1200ppm anomalous?"

    def test_parse_from_dict(self):
        data = {
            "type": "analysis_request",
            "from": "jetson-site-a",
            "to": "macmini-control",
            "message_id": "req-123",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "payload": {
                "question": "test question",
                "context": {"key": "value"},
                "lfm_thinking": "",
            },
        }
        msg = parse_message(data)
        assert isinstance(msg, AnalysisRequest)


class TestAnalysisResponse:
    def test_create(self):
        resp = AnalysisResponse(
            **{"from": "macmini-control"},
            to="jetson-site-a",
            in_reply_to="req-123",
            payload=AnalysisResponsePayload(
                answer="CO2 levels are elevated but not critical",
                confidence=0.8,
                reasoning={"mean_eco2": 500, "stdev": 100},
                lfm_thinking="Based on historical data...",
            ),
        )
        assert resp.type == MessageType.ANALYSIS_RESPONSE
        assert resp.in_reply_to == "req-123"
        assert resp.payload.confidence == 0.8


class TestDecision:
    def test_create(self):
        dec = Decision(
            participants=["jetson-site-a", "macmini-control"],
            payload=DecisionPayload(
                summary="CO2 elevated, check ventilation",
                consensus="action_recommended",
                reasoning={"source": "collaborative"},
            ),
        )
        assert dec.type == MessageType.DECISION
        assert len(dec.participants) == 2


class TestHeartbeat:
    def test_create(self):
        hb = Heartbeat(**{"from": "jetson-site-a", "status": AgentStatus.ACTIVE})
        assert hb.type == MessageType.HEARTBEAT
        assert hb.from_agent == "jetson-site-a"

    def test_serialization(self):
        hb = Heartbeat(**{"from": "jetson-site-a", "status": AgentStatus.ACTIVE})
        data = hb.model_dump(by_alias=True)
        assert data["from"] == "jetson-site-a"
        assert data["type"] == "heartbeat"


class TestAgentCard:
    def test_create(self):
        card = AgentCardPayload(
            agent_id="jetson-site-a",
            capabilities=["sensor_reading", "anomaly_detection"],
            model="LiquidAI/LFM2.5-1.2B-Thinking",
            endpoints=AgentEndpoints(
                a2a="http://localhost:8080/a2a/message",
                health="http://localhost:8080/health",
                stream="ws://localhost:8080/stream",
            ),
        )
        assert card.status == AgentStatus.ACTIVE
        assert card.agent_id == "jetson-site-a"


class TestParseMessage:
    def test_all_message_types(self):
        types_data = [
            {
                "type": "heartbeat",
                "from": "test",
                "timestamp": "2024-01-01T00:00:00+00:00",
                "status": "active",
            },
            {
                "type": "agent_card",
                "agent_id": "test",
                "capabilities": [],
                "model": "test",
                "endpoints": {"a2a": "x", "health": "y", "stream": "z"},
                "status": "active",
            },
        ]
        for data in types_data:
            msg = parse_message(data)
            assert msg is not None
