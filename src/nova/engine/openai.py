"""OpenAI - hosted GPT models over the chat completions endpoint."""

from __future__ import annotations

import os
from typing import Dict, List

from .. import config
from .base import Engine, EngineError, get_json, post_json


class OpenAIEngine(Engine):
    name = "openai"
    priority = 4

    URL = "https://api.openai.com/v1/chat/completions"
    MODELS = "https://api.openai.com/v1/models"

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        super().__init__(model or config.get("openai_model"))

    def probe(self) -> None:
        if not self.api_key:
            raise EngineError("OPENAI_API_KEY is not set")

    def list_models(self) -> List[str]:
        self.probe()
        data = get_json(self.MODELS, headers={"Authorization": f"Bearer {self.api_key}"})
        return sorted(m.get("id", "") for m in data.get("data", []) if m.get("id"))[:40]

    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        self.probe()
        data = post_json(
            self.URL,
            {"model": self.model, "messages": messages, "temperature": temperature},
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise EngineError(f"unexpected OpenAI payload: {str(data)[:200]}") from exc
