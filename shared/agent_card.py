"""Agent Card schema for agent discovery and capability advertisement."""

from __future__ import annotations

from shared.a2a_protocol import AgentCardPayload, AgentEndpoints, AgentStatus


def create_agent_card(
    agent_id: str,
    host: str,
    port: int,
    capabilities: list[str],
    model: str = "LiquidAI/LFM2.5-1.2B-Thinking",
) -> AgentCardPayload:
    """Create an Agent Card for advertising this agent's capabilities."""
    base_url = f"http://{host}:{port}"
    return AgentCardPayload(
        agent_id=agent_id,
        capabilities=capabilities,
        model=model,
        endpoints=AgentEndpoints(
            a2a=f"{base_url}/a2a/message",
            health=f"{base_url}/health",
            stream=f"ws://{host}:{port}/stream",
        ),
        status=AgentStatus.ACTIVE,
    )
