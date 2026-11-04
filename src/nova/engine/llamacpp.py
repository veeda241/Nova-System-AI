"""llama.cpp - a GGUF model from Hugging Face served on localhost by llama-server.

`llama-server -hf <repo>:<QUANT>` downloads one GGUF file and answers on an OpenAI-compatible
port, so any quant the user can name becomes Nova's engine with nothing installed per machine
beyond the llama.cpp binaries. No key, no quota, no router: the only requirement is that the
server process is running.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .. import config
from .base import Engine, EngineError, get_json, post_json

START_HINT = (
    "start it with `llama-server -hf unsloth/Qwen3-4B-Instruct-2507-GGUF:Q4_K_M --host 127.0.0.1 --port 8080`, "
    "or point `--model` at a .gguf already on disk"
)


class LlamaCppEngine(Engine):
    name = "llama"
    priority = 1
    is_local = True

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or config.get("llama_url") or "http://127.0.0.1:8080").rstrip("/")
        super().__init__(model or config.get("llama_model") or "")
        self._ready = False

    def served_models(self) -> List[str]:
        data = get_json(f"{self.base_url}/v1/models")
        return [m.get("id", "") for m in data.get("data", []) if isinstance(m, dict) and m.get("id")]

    def list_models(self) -> List[str]:
        return self.served_models()

    def probe(self) -> None:
        try:
            get_json(f"{self.base_url}/health")
        except EngineError as exc:
            if self._listening():
                raise EngineError(
                    f"llama-server is listening on {self.base_url} but reports no free slot - "
                    "the GGUF is still loading, or another request holds the context"
                ) from exc
            raise EngineError(f"llama-server is not reachable at {self.base_url} - {START_HINT}") from exc
        self._ready = True
        if not self.model:
            served = self.served_models()
            if not served:
                raise EngineError(f"llama-server at {self.base_url} serves no model - {START_HINT}")
            self.model = served[0]

    def _listening(self) -> bool:
        try:
            self.served_models()
        except EngineError:
            return False
        return True

    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        self.probe() if not self._ready else None
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": int(config.get("llama_max_tokens", 700)),
            "stream": False,
        }
        data = post_json(f"{self.base_url}/v1/chat/completions", payload)
        choices = data.get("choices") or []
        first = choices[0] if choices and isinstance(choices[0], dict) else {}
        text = ((first.get("message") or {}).get("content") or "").strip()
        if not text:
            raise EngineError(
                f"'{self.model}' answered with no content - raise --ctx-size or trim the prompt, "
                f"finish reason was '{first.get('finish_reason', 'none')}'"
            )
        return text
