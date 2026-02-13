"""A2A (Agent-to-Agent) protocol message types and utilities."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

import httpx
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    AGENT_CARD = "agent_card"
    SENSOR_OBSERVATION = "sensor_observation"
    ANALYSIS_REQUEST = "analysis_request"
    ANALYSIS_RESPONSE = "analysis_response"
    DECISION = "decision"
    HEARTBEAT = "heartbeat"
    QUERY = "query"
    QUERY_RESPONSE = "query_response"


class AgentStatus(str, Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    OFFLINE = "offline"


# --- Payload Models ---


class AgentEndpoints(BaseModel):
    a2a: str
    health: str
    stream: str


class AgentCardPayload(BaseModel):
    type: MessageType = MessageType.AGENT_CARD
    agent_id: str
    capabilities: list[str]
    model: str
    endpoints: AgentEndpoints
    status: AgentStatus = AgentStatus.ACTIVE


class SensorPayload(BaseModel):
    sensor: str = "ENS160+AHT21"
    temperature: float
    humidity: float
    eco2: int  # ppm
    tvoc: int  # ppb
    aqi: int  # 1-5 scale
    location: str


class AnalysisRequestPayload(BaseModel):
    question: str
    context: dict
    lfm_thinking: str = ""


class AnalysisResponsePayload(BaseModel):
    answer: str
    confidence: float
    reasoning: dict = {}
    lfm_thinking: str = ""


class DecisionPayload(BaseModel):
    summary: str
    consensus: str
    reasoning: dict = {}


class QueryPayload(BaseModel):
    question: str
    source: str = "dashboard"
    context: dict = {}


class QueryResponsePayload(BaseModel):
    answer: str
    data: dict = {}
    source_agent: str = ""


# --- Message Models ---


class A2AMessage(BaseModel):
    type: MessageType
    from_agent: str = Field(alias="from")
    to: Optional[str] = None
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    model_config = {"populate_by_name": True}


class SensorObservation(A2AMessage):
    type: MessageType = MessageType.SENSOR_OBSERVATION
    payload: SensorPayload


class AnalysisRequest(A2AMessage):
    type: MessageType = MessageType.ANALYSIS_REQUEST
    payload: AnalysisRequestPayload


class AnalysisResponse(A2AMessage):
    type: MessageType = MessageType.ANALYSIS_RESPONSE
    in_reply_to: str
    payload: AnalysisResponsePayload


class Decision(BaseModel):
    type: MessageType = MessageType.DECISION
    participants: list[str]
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    payload: DecisionPayload


class Heartbeat(BaseModel):
    type: MessageType = MessageType.HEARTBEAT
    from_agent: str = Field(alias="from")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: AgentStatus = AgentStatus.ACTIVE

    model_config = {"populate_by_name": True}


class Query(A2AMessage):
    type: MessageType = MessageType.QUERY
    payload: QueryPayload


class QueryResponse(A2AMessage):
    type: MessageType = MessageType.QUERY_RESPONSE
    in_reply_to: str = ""
    payload: QueryResponsePayload


# --- Utilities ---

MESSAGE_TYPE_MAP = {
    MessageType.SENSOR_OBSERVATION: SensorObservation,
    MessageType.ANALYSIS_REQUEST: AnalysisRequest,
    MessageType.ANALYSIS_RESPONSE: AnalysisResponse,
    MessageType.DECISION: Decision,
    MessageType.HEARTBEAT: Heartbeat,
    MessageType.AGENT_CARD: AgentCardPayload,
    MessageType.QUERY: Query,
    MessageType.QUERY_RESPONSE: QueryResponse,
}


def parse_message(data: dict) -> BaseModel:
    """Parse a raw dict into the appropriate A2A message model."""
    msg_type = MessageType(data["type"])
    model_class = MESSAGE_TYPE_MAP[msg_type]
    return model_class(**data)


async def send_message(
    url: str,
    message: BaseModel,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> dict | None:
    """Send an A2A message with exponential backoff retry."""
    import asyncio

    payload = message.model_dump(by_alias=True)

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(f"{url}/a2a/message", json=payload)
                resp.raise_for_status()
                return resp.json()
        except (httpx.HTTPError, httpx.ConnectError) as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2**attempt)
            await asyncio.sleep(delay)
    return None
