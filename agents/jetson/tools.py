"""Jetson agent tool functions for ADK.

Pure functions that the LLM agent can call as tools.  They read from
shared state (populated by the sensor loop) and from JSONL storage.
"""
from __future__ import annotations

from agents.jetson import config
from shared import state
from shared.storage import JSONLinesStorage


def get_latest_reading() -> dict:
    """Get the most recent sensor reading from the ENS160+AHT21 module.

    Returns:
        Dictionary with keys temperature, humidity, eco2, tvoc, aqi.
        Empty dict if no reading is available yet.
    """
    if state.previous_reading is None:
        return {}
    return state.previous_reading


def detect_anomalies(
    temperature: float,
    humidity: float,
    eco2: int,
    tvoc: int,
    aqi: int,
) -> dict:
    """Check sensor values against anomaly thresholds.

    Args:
        temperature: Temperature in Celsius.
        humidity: Relative humidity percentage.
        eco2: eCO2 concentration in ppm.
        tvoc: TVOC concentration in ppb.
        aqi: Air quality index on 1-5 scale.

    Returns:
        Dictionary with 'is_anomaly' boolean and 'reasons' list of strings.
    """
    reasons: list[str] = []

    if state.previous_reading is not None:
        prev_temp = state.previous_reading.get("temperature")
        if prev_temp is not None:
            delta = abs(temperature - prev_temp)
            if delta > config.TEMP_DELTA_THRESHOLD:
                reasons.append(
                    f"Temperature delta {delta:.1f}C exceeds "
                    f"{config.TEMP_DELTA_THRESHOLD}C threshold"
                )

    if eco2 > config.ECO2_THRESHOLD:
        reasons.append(
            f"eCO2 {eco2}ppm exceeds {config.ECO2_THRESHOLD}ppm threshold"
        )

    if tvoc > config.TVOC_THRESHOLD:
        reasons.append(
            f"TVOC {tvoc}ppb exceeds {config.TVOC_THRESHOLD}ppb threshold"
        )

    if aqi >= config.AQI_THRESHOLD:
        reasons.append(f"AQI {aqi} >= {config.AQI_THRESHOLD} (unhealthy)")

    return {"is_anomaly": len(reasons) > 0, "reasons": reasons}


def get_sensor_history(hours: int = 1) -> list:
    """Get historical sensor readings from storage.

    Args:
        hours: Number of hours of history to retrieve. Defaults to 1.

    Returns:
        List of sensor reading dictionaries.
    """
    storage = JSONLinesStorage(config.LOG_FILE)
    records = storage.read_recent(hours)
    return [r for r in records if r.get("event") == "sensor_reading"]
