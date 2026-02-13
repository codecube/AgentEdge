"""LFM 2.5 (Liquid Foundation Model) client wrapper."""
from __future__ import annotations

import asyncio
import importlib
import logging
from typing import AsyncGenerator

import torch
from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer

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

        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, trust_remote_code=True,
        )
        load_kwargs = dict(
            trust_remote_code=True,
            device_map="auto" if self.device == "cuda" else None,
            dtype=torch.float16 if self.device != "cpu" else torch.float32,
        )
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name, **load_kwargs,
            )
        except ValueError as e:
            if "Lfm2" not in str(e):
                raise
            # Some transformers versions ship a stub lfm2 module that shadows
            # the remote code.  Bypass AutoModelForCausalLM entirely and load
            # the model class directly from the HuggingFace repo.
            logger.warning("Local lfm2 module incomplete, loading from HF repo")
            config = AutoConfig.from_pretrained(
                model_name, trust_remote_code=True,
            )
            auto_map = getattr(config, "auto_map", {})
            class_ref = auto_map.get("AutoModelForCausalLM", "")
            if not class_ref:
                raise RuntimeError(
                    "Cannot load LFM: no AutoModelForCausalLM in repo auto_map. "
                    "Try: pip install -U transformers"
                ) from e
            mod_name, cls_name = class_ref.rsplit(".", 1)
            package = type(config).__module__.rsplit(".", 1)[0]
            modeling = importlib.import_module(f"{package}.{mod_name}")
            model_cls = getattr(modeling, cls_name)
            self.model = model_cls.from_pretrained(
                model_name,
                config=config,
                device_map=load_kwargs.get("device_map"),
                dtype=load_kwargs.get("dtype"),
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
