"""Tests for extracted tool functions (Jetson + Mac Mini)."""
from __future__ import annotations

import pytest

from shared import state


class TestJetsonTools:
    """Test agents/jetson/tools.py functions."""

    def setup_method(self):
        state.previous_reading = None

    def test_get_latest_reading_empty(self):
        from agents.jetson.tools import get_latest_reading

        assert get_latest_reading() == {}

    def test_get_latest_reading_with_data(self):
        from agents.jetson.tools import get_latest_reading

        state.previous_reading = {
            "temperature": 24.5,
            "humidity": 65.2,
            "eco2": 450,
            "tvoc": 120,
            "aqi": 1,
        }
        result = get_latest_reading()
        assert result["temperature"] == 24.5
        assert result["eco2"] == 450

    def test_detect_anomalies_normal(self):
        from agents.jetson.tools import detect_anomalies

        result = detect_anomalies(
            temperature=24.0, humidity=60.0, eco2=400, tvoc=100, aqi=1
        )
        assert result["is_anomaly"] is False
        assert result["reasons"] == []

    def test_detect_anomalies_eco2_high(self):
        from agents.jetson.tools import detect_anomalies

        result = detect_anomalies(
            temperature=24.0, humidity=60.0, eco2=1200, tvoc=100, aqi=1
        )
        assert result["is_anomaly"] is True
        assert any("eCO2" in r for r in result["reasons"])

    def test_detect_anomalies_tvoc_high(self):
        from agents.jetson.tools import detect_anomalies

        result = detect_anomalies(
            temperature=24.0, humidity=60.0, eco2=400, tvoc=600, aqi=1
        )
        assert result["is_anomaly"] is True
        assert any("TVOC" in r for r in result["reasons"])

    def test_detect_anomalies_aqi_high(self):
        from agents.jetson.tools import detect_anomalies

        result = detect_anomalies(
            temperature=24.0, humidity=60.0, eco2=400, tvoc=100, aqi=4
        )
        assert result["is_anomaly"] is True
        assert any("AQI" in r for r in result["reasons"])

    def test_detect_anomalies_temp_delta(self):
        from agents.jetson.tools import detect_anomalies

        state.previous_reading = {"temperature": 20.0}
        result = detect_anomalies(
            temperature=28.0, humidity=60.0, eco2=400, tvoc=100, aqi=1
        )
        assert result["is_anomaly"] is True
        assert any("Temperature delta" in r for r in result["reasons"])

    def test_detect_anomalies_temp_delta_within_threshold(self):
        from agents.jetson.tools import detect_anomalies

        state.previous_reading = {"temperature": 23.0}
        result = detect_anomalies(
            temperature=24.0, humidity=60.0, eco2=400, tvoc=100, aqi=1
        )
        assert result["is_anomaly"] is False

    def test_detect_anomalies_multiple(self):
        from agents.jetson.tools import detect_anomalies

        result = detect_anomalies(
            temperature=24.0, humidity=60.0, eco2=1200, tvoc=600, aqi=4
        )
        assert result["is_anomaly"] is True
        assert len(result["reasons"]) == 3


class TestMacMiniTools:
    """Test agents/macmini/tools.py functions."""

    def setup_method(self):
        state.sensor_history.clear()
        state.reasoning_events.clear()

    def test_compute_statistics_empty(self):
        from agents.macmini.tools import compute_statistics

        assert compute_statistics() == {}

    def test_compute_statistics_with_data(self):
        from agents.macmini.tools import compute_statistics

        state.sensor_history.extend([
            {"temperature": 22.0, "humidity": 60.0, "eco2": 400, "tvoc": 100, "aqi": 1},
            {"temperature": 24.0, "humidity": 65.0, "eco2": 500, "tvoc": 150, "aqi": 2},
            {"temperature": 26.0, "humidity": 70.0, "eco2": 600, "tvoc": 200, "aqi": 1},
        ])
        stats = compute_statistics()
        assert "temperature" in stats
        assert stats["temperature"]["mean"] == 24.0
        assert stats["temperature"]["count"] == 3
        assert stats["temperature"]["min"] == 22.0
        assert stats["temperature"]["max"] == 26.0

    def test_get_recent_history_empty(self):
        from agents.macmini.tools import get_recent_history

        assert get_recent_history() == []

    def test_get_recent_history_with_limit(self):
        from agents.macmini.tools import get_recent_history

        for i in range(10):
            state.sensor_history.append({"temperature": 20.0 + i})
        result = get_recent_history(limit=3)
        assert len(result) == 3
        assert result[-1]["temperature"] == 29.0

    def test_get_anomaly_summary_empty(self):
        from agents.macmini.tools import get_anomaly_summary

        summary = get_anomaly_summary()
        assert summary["count"] == 0
        assert summary["events"] == []

    def test_get_anomaly_summary_with_events(self):
        from agents.macmini.tools import get_anomaly_summary

        state.reasoning_events.append({"type": "anomaly", "reasons": ["test"]})
        summary = get_anomaly_summary()
        assert summary["count"] == 1
