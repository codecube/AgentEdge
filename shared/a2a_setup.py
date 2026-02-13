"""Wire A2A routes directly into a FastAPI app.

``to_a2a()`` returns a standalone Starlette app whose routes are added
during its *own* startup event.  When mounted as a sub-app under
FastAPI the startup never fires, so the routes are never registered.

This helper replicates what ``to_a2a()`` does internally but adds the
A2A routes to the **host** FastAPI app during its lifespan instead.
"""
from __future__ import annotations

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from fastapi import FastAPI
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
from google.adk.agents.base_agent import BaseAgent
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService


async def setup_a2a_routes(app: FastAPI, agent: BaseAgent, port: int) -> None:
    """Build the A2A agent card and add JSON-RPC routes to *app*.

    Call this inside the FastAPI ``lifespan`` context manager, **before**
    ``yield``, so the routes are available when the server starts
    accepting requests.
    """
    runner = Runner(
        app_name=agent.name or "adk_agent",
        agent=agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
        credential_service=InMemoryCredentialService(),
    )

    task_store = InMemoryTaskStore()
    agent_executor = A2aAgentExecutor(runner=runner)
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=task_store,
    )

    agent_card = await AgentCardBuilder(
        agent=agent,
        rpc_url=f"http://localhost:{port}/",
    ).build()

    a2a_app = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler,
    )
    a2a_app.add_routes_to_app(app)
