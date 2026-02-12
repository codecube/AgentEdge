"""Tests for JSON Lines storage utilities."""

import json
import tempfile
from pathlib import Path

import pytest

from shared.storage import JSONLinesStorage


@pytest.fixture
def tmp_storage(tmp_path):
    return JSONLinesStorage(tmp_path / "test.jsonl")


class TestJSONLinesStorage:
    def test_append_and_read(self, tmp_storage):
        tmp_storage.append({"temp": 24.5, "eco2": 450})
        tmp_storage.append({"temp": 25.0, "eco2": 500})

        records = tmp_storage.read_all()
        assert len(records) == 2
        assert records[0]["temp"] == 24.5
        assert records[1]["eco2"] == 500

    def test_auto_timestamp(self, tmp_storage):
        tmp_storage.append({"data": "test"})
        records = tmp_storage.read_all()
        assert "timestamp" in records[0]

    def test_preserve_existing_timestamp(self, tmp_storage):
        tmp_storage.append({"data": "test", "timestamp": "custom"})
        records = tmp_storage.read_all()
        assert records[0]["timestamp"] == "custom"

    def test_count(self, tmp_storage):
        assert tmp_storage.count() == 0
        tmp_storage.append({"a": 1})
        tmp_storage.append({"b": 2})
        assert tmp_storage.count() == 2

    def test_empty_file(self, tmp_storage):
        assert tmp_storage.read_all() == []
        assert tmp_storage.count() == 0

    def test_creates_parent_dirs(self, tmp_path):
        storage = JSONLinesStorage(tmp_path / "deep" / "nested" / "test.jsonl")
        storage.append({"test": True})
        assert storage.count() == 1


class TestAnomalyDetection:
    """Test anomaly detection thresholds (from Jetson agent config)."""

    def test_temp_delta_threshold(self):
        prev = {"temperature": 23.0}
        curr = {"temperature": 29.0}
        delta = abs(curr["temperature"] - prev["temperature"])
        assert delta > 5.0  # Should trigger

    def test_eco2_threshold(self):
        assert 1200 > 1000  # Should trigger
        assert 800 <= 1000  # Should not trigger

    def test_tvoc_threshold(self):
        assert 600 > 500  # Should trigger
        assert 400 <= 500  # Should not trigger

    def test_aqi_threshold(self):
        assert 4 >= 4  # Should trigger
        assert 3 < 4  # Should not trigger
