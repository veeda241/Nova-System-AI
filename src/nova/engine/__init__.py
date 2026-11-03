"""Engine registry: pick the best available runner, fail over on error."""

from __future__ import annotations

import time
from typing import Dict, List, Optional

from .. import config
from .base import Engine, EngineError, is_transient
from .gemini import GeminiEngine
from .groq import GroqEngine
from .ollama import OllamaEngine
from .openai import OpenAIEngine

__all__ = ["Engine", "EngineError", "Registry", "build_registry", "get_registry"]

FACTORIES = {
    "ollama": OllamaEngine,
    "groq": GroqEngine,
    "gemini": GeminiEngine,
    "openai": OpenAIEngine,
}


class Registry:
    def __init__(self, engines: List[Engine]):
        self.engines = engines
        self.active: Optional[Engine] = None
        self.last_error: Optional[str] = None

    def ordered(self) -> List[Engine]:
        return sorted(self.engines, key=lambda e: e.priority)

    def get(self, name: str) -> Engine:
        for engine in self.engines:
            if engine.name == name:
                return engine
        raise EngineError(f"unknown engine '{name}' - choose from {', '.join(self.names())}")

    def names(self) -> List[str]:
        return [e.name for e in self.ordered()]

    def select(self, preferred: str = "auto") -> Engine:
        """Return the first usable engine, local first by design."""
        if preferred and preferred != "auto":
            engine = self.get(preferred)
            engine.probe()
            self.active = engine
            return engine

        for engine in self.ordered():
            try:
                engine.probe()
            except EngineError as exc:
                self.last_error = f"{engine.name}: {exc}"
                continue
            self.active = engine
            return engine

        raise EngineError(self.exhausted_message())

    def exhausted_message(self) -> str:
        lines = [f"  - {e.name}: {e.available_reason()}" for e in self.ordered()]
        return "no engine is usable right now:\n" + "\n".join(lines) + "\nRun `nova doctor` for the full report."

    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.3, preferred: str = "auto") -> Dict[str, str]:
        """Complete with a retry on transient failures, then fail over down the priority list."""
        if preferred and preferred != "auto":
            engine = self.get(preferred)
            return {"engine": engine.name, "text": self._attempt(engine, messages, temperature)}

        errors: List[str] = []
        start = self.active or None
        candidates = self.ordered()
        if start is not None:
            candidates = [start] + [e for e in candidates if e is not start]

        for engine in candidates:
            try:
                engine.probe()
                text = self._attempt(engine, messages, temperature)
            except EngineError as exc:
                errors.append(f"{engine.name}: {exc}")
                continue
            self.active = engine
            return {"engine": engine.name, "text": text, "errors": errors}

        raise EngineError("every engine failed:\n" + "\n".join(f"  - {e}" for e in errors))

    @staticmethod
    def _attempt(engine: Engine, messages: List[Dict[str, str]], temperature: float, attempts: int = 3, pause: float = 4.0) -> str:
        last: Optional[EngineError] = None
        for attempt in range(1, attempts + 1):
            try:
                return engine.complete(messages, temperature)
            except EngineError as exc:
                last = exc
                if attempt >= attempts or not is_transient(str(exc)):
                    break
                time.sleep(pause * attempt)
        assert last is not None
        raise last

    def models(self, name: str = "auto") -> Dict[str, object]:
        if name and name != "auto":
            engine = self.get(name)
        else:
            engine = self.active or self.select("auto")
        return {"engine": engine.name, "current": engine.model, "models": engine.list_models()}

    def status(self) -> List[Dict[str, object]]:
        active = self.active.name if self.active else None
        rows = []
        for engine in self.ordered():
            rows.append(
                {
                    "name": engine.name,
                    "model": engine.model,
                    "available": engine.is_available(),
                    "reason": engine.available_reason(),
                    "local": engine.is_local,
                    "priority": engine.priority,
                    "active": engine.name == active,
                }
            )
        return rows


_registry: Optional[Registry] = None


def build_registry() -> Registry:
    config.load_env()
    return Registry([factory() for factory in FACTORIES.values()])


def get_registry() -> Registry:
    global _registry
    if _registry is None:
        _registry = build_registry()
    return _registry
