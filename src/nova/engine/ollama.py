"""Ollama - local, free, private. Preferred when the daemon is running."""

from __future__ import annotations

from typing import Any, Dict, List

from .. import config
from .base import Engine, EngineError, get_json, post_json

PREFERRED = ("llama3", "llama3.2", "mistral", "gemma", "qwen")


class OllamaEngine(Engine):
    name = "ollama"
    priority = 2
    is_local = True

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or config.get("ollama_url") or "http://localhost:11434").rstrip("/")
        self._installed: List[str] = []
        super().__init__(model or config.get("ollama_model"))

    def installed_models(self) -> List[str]:
        data = get_json(f"{self.base_url}/api/tags")
        return [m.get("name", "") for m in data.get("models", []) if m.get("name")]

    def list_models(self) -> List[str]:
        return self.installed_models()

    def probe(self) -> None:
        try:
            self._installed = self.installed_models()
        except EngineError as exc:
            raise EngineError(f"Ollama is not reachable at {self.base_url} - start it with `ollama serve`") from exc
        if not self._installed:
            raise EngineError(f"Ollama is running but no model is pulled - try `ollama pull {self.model}`")
        if not self.model:
            self.model = self._pick(self._installed)

    @staticmethod
    def _pick(models: List[str]) -> str:
        for want in PREFERRED:
            for model in models:
                if want in model.lower():
                    return model
        return models[0]

    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        self.probe() if not self._installed else None
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        data = post_json(f"{self.base_url}/api/chat", payload)
        text = (data.get("message") or {}).get("content", "").strip()
        if not text:
            raise EngineError(f"Ollama model '{self.model}' returned an empty completion")
        return text
