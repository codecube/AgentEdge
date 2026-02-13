"""LFM 2.5 (Liquid Foundation Model) client wrapper — Ollama backend."""
from __future__ import annotations

import json
import logging
import os
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")


class LFMClient:
    """Wrapper for Liquid AI LFM2.5 via Ollama HTTP API."""

    def __init__(self, model_name: str = "lfm2.5-thinking"):
        self.model = model_name
        self.base_url = OLLAMA_URL
        logger.info("LFM client: model=%s, ollama=%s", self.model, self.base_url)

        # Verify Ollama is reachable (sync check at init time)
        try:
            resp = httpx.get(f"{self.base_url}/api/tags", timeout=5.0)
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            # Ollama may include :latest suffix
            matched = any(
                m == self.model or m.startswith(f"{self.model}:")
                for m in models
            )
            if matched:
                logger.info("LFM model available in Ollama")
            else:
                logger.warning(
                    "Model %s not found in Ollama (available: %s). "
                    "Run: ollama pull %s",
                    self.model, models, self.model,
                )
        except Exception as e:
            logger.warning("Cannot reach Ollama at %s: %s", self.base_url, e)

        logger.info("LFM client ready")

    async def analyze(self, prompt: str, max_tokens: int = 256) -> str:
        """Run analysis and return full response text."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": max_tokens,
                    },
                },
            )
            resp.raise_for_status()
            return resp.json().get("response", "")

    async def analyze_streaming(
        self, prompt: str, max_tokens: int = 256
    ) -> AsyncGenerator[str, None]:
        """Generate response tokens for streaming display."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": max_tokens,
                    },
                },
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    token = data.get("response", "")
                    if token:
                        yield token
                    if data.get("done", False):
                        break
