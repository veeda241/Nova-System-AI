"""Optional voice. Off by default; every provider reports honestly when absent."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Optional

from . import config


def providers() -> Dict[str, str]:
    found: Dict[str, str] = {}
    try:
        import pyttsx3  # noqa: F401

        found["tts"] = "pyttsx3"
    except ImportError:
        pass
    if "tts" not in found:
        try:
            import edge_tts  # noqa: F401

            found["tts"] = "edge-tts" if shutil.which("ffmpeg") or shutil.which("ffplay") else "edge-tts (needs ffmpeg or ffplay to play audio)"
        except ImportError:
            pass
    if "tts" not in found:
        try:
            import soprano  # noqa: F401

            found["tts"] = "soprano"
        except ImportError:
            pass

    try:
        import whisper  # noqa: F401

        found["stt"] = "whisper"
    except ImportError:
        try:
            import speech_recognition  # noqa: F401

            found["stt"] = "speech-recognition"
        except ImportError:
            pass
    return found


def status() -> Dict[str, Any]:
    return {"enabled": config.get("voice", "off") == "on", **providers(), "player": shutil.which("ffplay") or shutil.which("mpg123") or shutil.which("afplay")}


def set_enabled(on: bool) -> Dict[str, Any]:
    settings = config.save_settings({"voice": "on" if on else "off"})
    return {"ok": True, "voice": settings["voice"], "providers": providers()}


def say(text: str) -> Dict[str, Any]:
    if config.get("voice", "off") != "on":
        return {"ok": False, "error": "voice is off - enable it with `nova voice on`"}
    which = providers().get("tts")
    if not which:
        return {"ok": False, "error": "no TTS engine installed - `pip install pyttsx3` (offline) or `pip install edge-tts` (network)"}

    name = which.split()[0]
    try:
        if name == "pyttsx3":
            import pyttsx3

            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            return {"ok": True, "provider": name}
        if name == "edge-tts":
            import asyncio

            import edge_tts

            media = shutil.which("ffplay") or shutil.which("mpg123")
            if not media:
                return {"ok": False, "error": "edge-tts can synthesise but nothing can play the audio - install ffmpeg"}
            path = os.path.join(tempfile.gettempdir(), "nova_say.mp3")
            asyncio.run(edge_tts.Communicate(text, "en-US-AriaNeural").save(path))
            subprocess.run([media, "-nodisp", "-autoexit", "-loglevel", "quiet", path], check=False, timeout=120)
            return {"ok": True, "provider": name, "audio": path}
        if name == "soprano":
            import soprano

            soprano.say(text)
            return {"ok": True, "provider": name}
    except Exception as exc:
        return {"ok": False, "error": f"{name} failed: {exc}"}
    return {"ok": False, "error": f"unsupported TTS provider '{which}'"}


def listen(timeout: int = 6, model: str = "tiny") -> Dict[str, Any]:
    if config.get("voice", "off") != "on":
        return {"ok": False, "error": "voice is off - enable it with `nova voice on`"}
    which = providers().get("stt")
    if not which:
        return {"ok": False, "error": "no STT engine installed - `pip install openai-whisper` or `pip install SpeechRecognition`"}
    try:
        if which == "whisper":
            import whisper

            import sounddevice  # noqa: F401
    except ImportError:
        return {"ok": False, "error": "whisper is installed but recording needs `pip install sounddevice`"}

    try:
        import numpy as np
        import sounddevice as sd
        import whisper

        frames = sd.rec(int(timeout * 16000), samplerate=16000, channels=1, dtype="int16")
        sd.wait()
        audio = frames.flatten().astype("float32") / 32768.0
        model_obj = whisper.load_model(model)
        result = model_obj.transcribe(audio, fp16=False)
        return {"ok": True, "text": result.get("text", "").strip(), "provider": which}
    except Exception as exc:
        return {"ok": False, "error": f"listening failed: {exc}"}
