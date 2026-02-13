"""LFM 2.5 (Liquid Foundation Model) client wrapper."""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

logger = logging.getLogger(__name__)


class LFMClient:
    """Wrapper for Liquid AI LFM2.5-1.2B-Thinking model."""

    def __init__(self, model_name: str = "LiquidAI/LFM2.5-1.2B-Thinking"):
        logger.info("Loading LFM model: %s", model_name)

        # Detect device
        if torch.cuda.is_available():
            self.device = "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            self.device = "mps"
        else:
            self.device = "cpu"
        logger.info("Using device: %s", self.device)

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="auto" if self.device == "cuda" else None,
            torch_dtype=torch.float16 if self.device != "cpu" else torch.float32,
        )
        if self.device == "mps":
            self.model = self.model.to("mps")

        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        logger.info("LFM model loaded successfully")

    async def analyze(self, prompt: str, max_tokens: int = 256) -> str:
        """Run analysis and return full response text."""
        result = []
        async for token in self.analyze_streaming(prompt, max_tokens):
            result.append(token)
        return "".join(result)

    async def analyze_streaming(
        self, prompt: str, max_tokens: int = 256
    ) -> AsyncGenerator[str, None]:
        """Generate response tokens one at a time for streaming display."""
        inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
        inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        streamer = TextIteratorStreamer(
            self.tokenizer, skip_prompt=True, skip_special_tokens=True
        )

        generation_kwargs = {
            **inputs,
            "max_new_tokens": max_tokens,
            "do_sample": True,
            "temperature": 0.7,
            "top_p": 0.9,
            "streamer": streamer,
        }

        # Run generation in a thread to not block the event loop
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, lambda: self.model.generate(**generation_kwargs))

        for token_text in streamer:
            yield token_text
            await asyncio.sleep(0)  # Yield control to event loop
