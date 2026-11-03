"""Engine primitive: model runners that turn a prompt into text."""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import requests


class EngineError(RuntimeError):
    """Raised when an engine cannot serve a request."""

    def __str__(self) -> str:
        return scrub(super().__str__())


def scrub(text: str) -> str:
    """Never let an API key escape inside an error message."""
    if not text:
        return text
    text = re.sub(r"([?&](?:key|access_token|api_key)=)[^&\s\"']+", r"\1***", text)
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]{12,}", r"\1***", text)
    text = re.sub(r"AIza[0-9A-Za-z_\-]{20,}", "AIza***", text)
    text = re.sub(r"sk-[A-Za-z0-9_\-\.]{12,}", "sk-***", text)
    text = re.sub(r"gsk_[A-Za-z0-9_\-]{12,}", "gsk_***", text)
    return text


TRANSIENT_MARKERS = ("http 429", "http 500", "http 502", "http 503", "http 504", "unavailable", "high demand", "rate limit", "timed out", "cannot reach")


def is_transient(message: str) -> bool:
    """True when retrying the same engine is more likely to help than switching away."""
    low = (message or "").lower()
    return any(marker in low for marker in TRANSIENT_MARKERS)


class Engine(ABC):
    name = "base"
    priority = 100
    is_local = False

    def __init__(self, model: Optional[str] = None, timeout: int = 90):
        self.model = model
        self.timeout = timeout

    @abstractmethod
    def probe(self) -> None:
        """Raise EngineError if this engine cannot be used right now."""

    @abstractmethod
    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        """Send an OpenAI-style message list, return assistant text."""

    def is_available(self) -> bool:
        try:
            self.probe()
            return True
        except EngineError:
            return False

    def available_reason(self) -> str:
        try:
            self.probe()
            return "ready"
        except EngineError as exc:
            return str(exc)

    def list_models(self) -> List[str]:
        raise EngineError(f"{self.name} cannot list models")

    @property
    def label(self) -> str:
        return f"{self.name}:{self.model}" if self.model else self.name

    def __repr__(self) -> str:
        return f"<Engine {self.name} {self.model or ''}>"


def post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    safe_url = scrub(url)
    try:
        response = requests.post(url, json=payload, headers=headers or {}, timeout=120)
    except requests.exceptions.ConnectionError as exc:
        raise EngineError(f"cannot reach {safe_url} ({exc.__class__.__name__})") from exc
    except requests.exceptions.Timeout as exc:
        raise EngineError(f"timed out after {exc.timeout or 120}s talking to {safe_url}") from exc
    except requests.exceptions.RequestException as exc:
        raise EngineError(f"request to {safe_url} failed: {scrub(str(exc))}") from exc

    try:
        data = response.json()
    except ValueError:
        raise EngineError(f"{safe_url} returned non-JSON (HTTP {response.status_code}): {scrub(response.text[:200])}") from None

    if response.status_code >= 400:
        detail = data.get("error") if isinstance(data, dict) else None
        detail = detail or data
        message = f"HTTP {response.status_code} from {safe_url}: {scrub(json.dumps(detail, default=str)[:300])}"
        if response.status_code == 404 and "is not found" in str(detail):
            message += "\n  the model name is wrong or retired - list yours with `nova engine models`"
        if response.status_code == 401:
            message += "\n  the API key was rejected - check it in .env"
        if response.status_code == 429:
            message += "\n  rate limited - wait, or switch engine with `nova engine use <name>`"
        raise EngineError(message)
    return data


def get_json(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    safe_url = scrub(url)
    try:
        response = requests.get(url, params=params, headers=headers or {}, timeout=10)
    except requests.exceptions.RequestException as exc:
        raise EngineError(f"cannot reach {safe_url} ({exc.__class__.__name__})") from exc
    try:
        data = response.json()
    except ValueError:
        raise EngineError(f"{safe_url} returned non-JSON (HTTP {response.status_code})") from None
    if response.status_code >= 400:
        raise EngineError(f"HTTP {response.status_code} from {safe_url}")
    return data
