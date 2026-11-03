"""Gemini - REST generateContent, so no google-generativeai install is needed."""

from __future__ import annotations

import os
from typing import Any, Dict, List

from .. import config
from .base import Engine, EngineError, get_json, post_json

BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiEngine(Engine):
    name = "gemini"
    priority = 4

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        super().__init__(model or config.get("gemini_model"))

    def probe(self) -> None:
        if not self.api_key:
            raise EngineError("GEMINI_API_KEY is not set - create one at aistudio.google.com/apikey")

    def list_models(self) -> List[str]:
        self.probe()
        data = get_json(BASE, params={"key": self.api_key, "pageSize": 200})
        usable = []
        for entry in data.get("models", []):
            methods = entry.get("supportedGenerationMethods") or []
            if "generateContent" in methods:
                usable.append(entry.get("name", "").split("/")[-1])
        return sorted(usable)

    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        self.probe()
        system_text = "\n".join(m["content"] for m in messages if m.get("role") == "system")
        contents: List[Dict[str, Any]] = [
            {"role": "user" if m.get("role") == "user" else "model", "parts": [{"text": m["content"]}]}
            for m in messages
            if m.get("role") != "system"
        ]
        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}

        url = f"{BASE}/{self.model}:generateContent?key={self.api_key}"
        data = post_json(url, payload)
        try:
            parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError) as exc:
            block = data.get("promptFeedback") or data.get("error") or {}
            raise EngineError(f"Gemini returned no candidates ({str(block)[:160]})") from exc
        return "".join(part.get("text", "") for part in parts).strip()
