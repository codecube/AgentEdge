"""JSON Lines storage utilities for agent logs and sensor data."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class JSONLinesStorage:
    """Append-only JSON Lines file storage."""

    def __init__(self, file_path: str | Path):
        self.path = Path(file_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, record: dict) -> None:
        """Append a record with automatic timestamp."""
        if "timestamp" not in record:
            record["timestamp"] = datetime.now(timezone.utc).isoformat()
        with open(self.path, "a") as f:
            f.write(json.dumps(record) + "\n")

    def read_all(self) -> list[dict]:
        """Read all records from the file."""
        if not self.path.exists():
            return []
        records = []
        with open(self.path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning("Skipping malformed line: %s", line[:80])
        return records

    def read_recent(self, hours: float = 24.0) -> list[dict]:
        """Read records from the last N hours."""
        cutoff = datetime.now(timezone.utc).timestamp() - (hours * 3600)
        records = []
        for record in self.read_all():
            ts = record.get("timestamp", "")
            try:
                record_time = datetime.fromisoformat(ts).timestamp()
                if record_time >= cutoff:
                    records.append(record)
            except (ValueError, TypeError):
                continue
        return records

    def count(self) -> int:
        """Count total records."""
        if not self.path.exists():
            return 0
        with open(self.path) as f:
            return sum(1 for line in f if line.strip())
