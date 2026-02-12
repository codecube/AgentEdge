"""Tests for agent card creation."""

from shared.agent_card import create_agent_card


class TestCreateAgentCard:
    def test_creates_valid_card(self):
        card = create_agent_card(
            agent_id="jetson-site-a",
            host="192.168.1.10",
            port=8080,
            capabilities=["sensor_reading", "anomaly_detection"],
        )
        assert card.agent_id == "jetson-site-a"
        assert card.model == "LiquidAI/LFM-2.5-1B"
        assert card.endpoints.a2a == "http://192.168.1.10:8080/a2a/message"
        assert card.endpoints.health == "http://192.168.1.10:8080/health"
        assert card.endpoints.stream == "ws://192.168.1.10:8080/stream"
        assert "sensor_reading" in card.capabilities

    def test_serializes_to_dict(self):
        card = create_agent_card(
            agent_id="macmini-control",
            host="localhost",
            port=8081,
            capabilities=["historical_analysis"],
        )
        data = card.model_dump()
        assert data["agent_id"] == "macmini-control"
        assert data["status"] == "active"
