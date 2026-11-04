"""Hugging Face Inference Providers - hosted models through one token, nothing installed.

One HTTPS call to `https://router.huggingface.co/v1/chat/completions` with a Bearer
HF_TOKEN reaches hundreds of hosted models on any machine, which is what makes this the
"works on any laptop" engine. It is *not* free: Hugging Face gives free user accounts no
included Inference Providers credits, so a routed call either draws on purchased credits or
comes back 402. That distinction is spelled out in the errors instead of pretending the call
would succeed.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from .. import config
from .base import Engine, EngineError, get_json, post_json

ROUTER = "https://router.huggingface.co/v1"
MODEL_LIST_LIMIT = 80


class HuggingFaceEngine(Engine):
    name = "hf"
    priority = 3
    is_local = False

    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("HF_TOKEN") or ""
        super().__init__(model or config.get("hf_model") or "meta-llama/Llama-3.1-8B-Instruct:fastest")
        self.list_note = ""

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def probe(self) -> None:
        if not self.api_key:
            raise EngineError(
                "HF_TOKEN is not set - create a fine-grained token with the 'Make calls to Inference "
                "Providers' permission at huggingface.co/settings/tokens, then put HF_TOKEN in .env"
            )

    def list_models(self) -> List[str]:
        self.probe()
        data = get_json(f"{ROUTER}/models", headers=self._headers())
        entries = data.get("data") if isinstance(data, dict) else data
        ids = sorted({str(item["id"]) for item in entries or [] if isinstance(item, dict) and item.get("id")})
        self.list_note = (
            f"showing the first {MODEL_LIST_LIMIT} of {len(ids)} served models - add --json for the full list"
            if len(ids) > MODEL_LIST_LIMIT
            else ""
        )
        return ids[:MODEL_LIST_LIMIT]

    def complete(self, messages: List[Dict[str, str]], temperature: float = 0.3) -> str:
        self.probe()
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": int(config.get("hf_max_tokens", 700)),
            "stream": False,
        }
        try:
            data = post_json(f"{ROUTER}/chat/completions", payload, headers=self._headers())
        except EngineError as exc:
            raise _explain(exc) from None

        choices = data.get("choices") or []
        first = choices[0] if choices and isinstance(choices[0], dict) else {}
        text = ((first.get("message") or {}).get("content") or "").strip()
        if not text:
            raise EngineError(f"the router answered with no content for '{self.model}' - try another model from `nova engine models hf`")
        return text


def _explain(exc: EngineError) -> EngineError:
    """Turn the router's status codes into the action Nova's user can actually take."""
    text = str(exc)
    low = text.lower()
    if "http 401" in low or "http 403" in low:
        text += "\n  HF_TOKEN was refused - it needs the 'Make calls to Inference Providers' permission (a fine-grained token works)"
    if "http 402" in low or "credit" in low or "billing" in low or "payment" in low:
        text += (
            "\n  this account has no Inference Providers credit - free accounts get none included and PRO gets $2/month, "
            "so either buy credits at huggingface.co/settings/billing or use the free local engine: `nova engine use ollama`"
        )
    if "http 404" in low or "not found" in low:
        text += "\n  that model id is not served - `nova engine models hf` lists what your token can call, or append :fastest"
    if "http 429" in low:
        text += "\n  provider rate limited - `nova config set hf_model <id>:cheapest` spreads the load across providers"
    return EngineError(text)
