"""Groq - fast hosted inference over the OpenAI-compatible endpoint."""

from __future__ import annotations

import os
from typing import Dict, List

from .. import config
from .base import Engine, EngineError, get_json, post_json


class GroqEngine(Engine):
    name = "groq"
    priority = 3

    URL = "https://api.groq.com/openai/v1/chat/completions"
    MODELS = "https://api.groq.com/openai/v1/models"

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GROQ_API_KEY")
        super().__init__(model or config.get("groq_model"))

    def probe(self) -> None:
        if not self.api_key:
            raise EngineError("GROQ_API_KEY is not set - get a key at console.groq.com and put it in .env")

    def list_models(self) -> List[str]:
        self.probe()
        data = get_json(self.MODELS, headers={"Authorization": f"Bearer {self.api_key}"})
        return sorted(m.get("id", "") for m in data.get("data", []) if m.get("id"))

    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        self.probe()
        data = post_json(
            self.URL,
            {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": 4096},
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise EngineError(f"unexpected Groq payload: {str(data)[:200]}") from exc
