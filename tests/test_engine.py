"""Engine selection, failover, retries and secret scrubbing - no network needed."""

from __future__ import annotations

import pytest

import nova.engine as engine_pkg
from nova.engine import Registry
from nova.engine.base import Engine, EngineError, is_transient, scrub
from nova.engine.gemini import GeminiEngine
from nova.engine.huggingface import HuggingFaceEngine
from nova.engine.ollama import OllamaEngine


class Stub(Engine):
    def __init__(self, name, priority, usable=True, failures=0, transient=True, reply="ok"):
        self.name = name
        self.priority = priority
        self.usable = usable
        self.failures = failures
        self.transient = transient
        self.reply = reply
        self.calls = 0
        self.model = "stub-model"

    def probe(self) -> None:
        if not self.usable:
            raise EngineError(f"{self.name} is configured out")

    def complete(self, messages, temperature=0.3):
        self.calls += 1
        if self.calls <= self.failures:
            code = "HTTP 503 high demand" if self.transient else "HTTP 401 bad key"
            raise EngineError(f"{self.name} {code}")
        return f"{self.reply}:{self.name}"


def test_select_prefers_lowest_priority_number():
    hosted, local = Stub("gemini", 3), Stub("ollama", 1, reply="local")
    registry = Registry([hosted, local])
    assert registry.select("auto").name == "ollama"


def test_select_reports_why_every_engine_was_rejected():
    registry = Registry([Stub("ollama", 1, usable=False), Stub("groq", 2, usable=False)])
    with pytest.raises(EngineError) as exc:
        registry.select("auto")
    message = str(exc.value)
    assert "no engine is usable" in message and "ollama" in message and "groq" in message


def test_complete_fails_over_to_the_next_engine():
    first, second = Stub("ollama", 1, failures=99, transient=False), Stub("gemini", 3)
    registry = Registry([first, second])
    reply = registry.complete([{"role": "user", "content": "x"}], preferred="auto")
    assert reply["engine"] == "gemini" and reply["text"].endswith("gemini")
    assert reply["errors"] and "ollama" in reply["errors"][0]


def test_transient_failures_are_retried_then_succeed(monkeypatch):
    slept = []
    monkeypatch.setattr(engine_pkg.time, "sleep", lambda seconds: slept.append(seconds))
    flaky = Stub("gemini", 3, failures=2, transient=True)
    registry = Registry([flaky])
    reply = registry.complete([{"role": "user", "content": "x"}], preferred="gemini")
    assert reply["text"] == "ok:gemini"
    assert flaky.calls == 3
    assert len(slept) == 2


def test_permanent_failures_are_not_retried(monkeypatch):
    monkeypatch.setattr(engine_pkg.time, "sleep", lambda seconds: None)
    engine = Stub("openai", 4, failures=99, transient=False)
    registry = Registry([engine])
    with pytest.raises(EngineError):
        registry.complete([{"role": "user", "content": "x"}], preferred="openai")
    assert engine.calls == 1


def test_forced_engine_does_not_fail_over():
    good, bad = Stub("gemini", 3), Stub("ollama", 1, failures=99, transient=False)
    registry = Registry([good, bad])
    with pytest.raises(EngineError):
        registry.complete([{"role": "user", "content": "x"}], preferred="ollama")
    assert good.calls == 0


def test_status_lists_reasons_and_active_flag():
    active = Stub("gemini", 3)
    registry = Registry([Stub("ollama", 1, usable=False), active])
    registry.select("auto")
    rows = {row["name"]: row for row in registry.status()}
    assert rows["ollama"]["available"] is False and "configured out" in rows["ollama"]["reason"]
    assert rows["gemini"]["available"] is True and rows["gemini"]["active"] is True


def test_unknown_engine_name_is_an_error():
    registry = Registry([Stub("gemini", 3)])
    with pytest.raises(EngineError) as exc:
        registry.get("mistral")
    assert "unknown engine" in str(exc.value)


def test_scrub_masks_every_key_shape():
    text = "?key=AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ012345 Bearer gsk_abcdefghijklmnopqrstuvwxyz1234 sk-abcdefghijklmnop1234 hf_AAAAAAAAAAAAAAAAAAAAAAAAAAA"
    cleaned = scrub(text)
    for secret in ("AIzaSyABCDEFGHI", "gsk_abcdefghijk", "sk-abcdefghijkl", "hf_AAAAAAAAAAAAAAAAAAAAAAAAAAA"):
        assert secret not in cleaned
    assert "***" in cleaned


def test_engine_error_string_is_scrubbed():
    assert "AIzaSyDUMMYDUMMYDUMMY123456" not in str(EngineError("url had AIzaSyDUMMYDUMMYDUMMY123456"))


def test_transient_detection():
    assert is_transient("HTTP 503 This model is experiencing high demand")
    assert is_transient("HTTP 429 rate limited")
    assert not is_transient("HTTP 404 model not found")


def test_ollama_reports_the_actionable_fix():
    engine = OllamaEngine(base_url="http://127.0.0.1:9")
    assert engine.is_available() is False
    assert "ollama serve" in engine.available_reason()


def test_the_engine_probes_the_url_named_in_the_environment(sandbox, monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:9")
    engine = OllamaEngine()
    assert engine.base_url == "http://127.0.0.1:9"
    assert engine.is_available() is False


def test_a_saved_setting_does_not_override_the_environment(sandbox, monkeypatch):
    from nova import config

    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5")
    config.save_settings({"ollama_model": "llama3.2"})
    assert OllamaEngine().model == "qwen2.5"


def test_a_flag_beats_the_environment(sandbox, monkeypatch):
    from nova import config

    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5")
    config.override("ollama_model", "llama3.2")
    assert OllamaEngine().model == "llama3.2"


def test_gemini_without_a_key_explains_where_to_get_one(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    engine = GeminiEngine()
    assert "aistudio.google.com/apikey" in engine.available_reason()


def test_default_gemini_model_is_a_current_one():
    from nova import config

    assert "1.5" not in str(config.DEFAULTS["gemini_model"])


def test_models_requires_an_engine_that_supports_listing():
    registry = Registry([Stub("gemini", 3)])
    with pytest.raises(EngineError) as exc:
        registry.models("gemini")
    assert "cannot list models" in str(exc.value)


def test_hf_without_a_token_explains_which_permission_the_token_needs(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    reason = HuggingFaceEngine().available_reason()
    assert "HF_TOKEN is not set" in reason and "Inference Providers" in reason


def test_hf_completion_without_a_token_never_reaches_the_network(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    with pytest.raises(EngineError) as exc:
        HuggingFaceEngine().complete([{"role": "user", "content": "hi"}])
    assert "HF_TOKEN" in str(exc.value)


def test_factories_are_ordered_local_first_then_hosted():
    order = sorted((cls.priority, name) for name, cls in engine_pkg.FACTORIES.items())
    assert [name for _, name in order] == ["llama", "ollama", "hf", "groq", "gemini", "openai"]


def llama_payload(url: str, **kwargs):
    if url.endswith("/health"):
        return {"status": "ok"}
    return {"data": [{"id": "qwen3-4b-instruct-2507-q4_k_m"}]}


def test_llama_adopts_the_model_the_server_is_serving(monkeypatch):
    from nova.engine import llamacpp

    monkeypatch.setattr(llamacpp, "get_json", llama_payload)
    engine = llamacpp.LlamaCppEngine(base_url="http://127.0.0.1:8080")
    engine.probe()
    assert engine.model == "qwen3-4b-instruct-2507-q4_k_m"


def test_llama_talks_openai_compatible_to_the_local_port(monkeypatch):
    from nova.engine import llamacpp

    seen = {}

    def fake_post(url, payload, headers=None):
        seen["url"] = url
        seen["payload"] = payload
        return {"choices": [{"message": {"content": "  hello  "}}]}

    monkeypatch.setattr(llamacpp, "get_json", llama_payload)
    monkeypatch.setattr(llamacpp, "post_json", fake_post)
    engine = llamacpp.LlamaCppEngine(base_url="http://127.0.0.1:8080")
    assert engine.complete([{"role": "user", "content": "hi"}]) == "hello"
    assert seen["url"] == "http://127.0.0.1:8080/v1/chat/completions"
    assert seen["payload"]["model"] == "qwen3-4b-instruct-2507-q4_k_m"


def test_llama_names_the_command_that_starts_the_server():
    from nova.engine.llamacpp import LlamaCppEngine

    reason = LlamaCppEngine(base_url="http://127.0.0.1:9").available_reason()
    assert "not reachable" in reason and "llama-server -hf" in reason


def test_a_busy_llama_server_is_not_reported_as_missing(monkeypatch):
    from nova.engine import llamacpp

    def busy(url, **kwargs):
        if url.endswith("/health"):
            raise llamacpp.EngineError("HTTP 503 from http://127.0.0.1:8080/health")
        return llama_payload(url)

    monkeypatch.setattr(llamacpp, "get_json", busy)
    reason = llamacpp.LlamaCppEngine(base_url="http://127.0.0.1:8080").available_reason()
    assert "no free slot" in reason and "not reachable" not in reason


def test_the_hf_model_comes_from_settings(sandbox, monkeypatch):
    from nova import config

    monkeypatch.setenv("HF_TOKEN", "hf_" + "x" * 30)
    config.override("hf_model", "Qwen/Qwen3-4B:cheapest")
    assert HuggingFaceEngine().model == "Qwen/Qwen3-4B:cheapest"


def test_no_credit_says_so_instead_of_looking_like_a_bug():
    from nova.engine.huggingface import _explain

    message = str(_explain(EngineError("HTTP 402 from https://router.huggingface.co/v1/chat/completions: payment required")))
    assert "free accounts get none" in message and "ollama" in message


def test_a_router_error_cannot_carry_the_token(sandbox):
    from nova.engine.huggingface import _explain

    secret = "hf_" + "Z" * 34
    message = str(_explain(EngineError("HTTP 401 from x: {'error': 'invalid " + secret + "'}")))
    assert secret not in message and "hf_***" in message
