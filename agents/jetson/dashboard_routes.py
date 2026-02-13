"""Jetson dashboard REST routes — served alongside the A2A endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from shared import state

router = APIRouter()


@router.get("/sensor/current")
async def sensor_current():
    """Return the latest sensor reading."""
    if state.previous_reading is None:
        return {"status": "no_data", "reading": None}
    return {"status": "ok", "reading": state.previous_reading}
