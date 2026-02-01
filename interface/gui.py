#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SimpliSmart UI (STT + Wake Word + UI)
====================================
Integrated HUD with Voice Support, talking to Nova API.
"""

import os
import sys
import time
import json
import threading
import requests
import subprocess
from datetime import datetime
from pathlib import Path

# Qt Imports
try:
    from PyQt6.QtCore import Qt, QUrl, QObject, pyqtSlot, pyqtSignal, QTimer, QThread
    from PyQt6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu
    from PyQt6.QtGui import QIcon, QAction
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebChannel import QWebChannel
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False

# Voice System Imports
try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

# Import NOVA Voice Engine (Soprano TTS)
try:
    from nova_system.tts import get_nova_voice, nova_say, NovaVoice, SOPRANO_AVAILABLE
    NOVA_VOICE_AVAILABLE = True
except ImportError:
    NOVA_VOICE_AVAILABLE = False
    SOPRANO_AVAILABLE = False

try:
    import piper
    PIPER_AVAILABLE = True
except ImportError:
    PIPER_AVAILABLE = False

SCRIPT_DIR = Path(__file__).parent.resolve()
PIPER_MODEL_PATH = SCRIPT_DIR / "models" / "piper" / "en_US-lessac-low.onnx"

# Initialize Nova Voice
_nova_voice = None

def get_voice():
    """Get Nova Voice engine."""
    global _nova_voice
    if _nova_voice is None and NOVA_VOICE_AVAILABLE:
        _nova_voice = get_nova_voice()
    return _nova_voice

def nova_speak(text):
    """Speak text using Nova Voice (Soprano TTS)."""
    voice = get_voice()
    if voice:
        try:
            return voice.say(text)
        except:
            pass
    return powershell_tts(text)

def piper_tts(text):
    """Speak text using Nova Voice (legacy alias)."""
    return nova_speak(text)
    
    try:
        # Piper usually requires calling the command line or using the lib
        # For simplicity and reliability on Windows, calling the piper command is often easier
        # if piper-tts was installed as a tool.
        # But we'll try to use a temporary wav file and play it.
        import tempfile
        import wave
        
        output_wav = Path(tempfile.gettempdir()) / "nova_speech.wav"
        
        # Command for piper
        # piper --model en_US-lessac-low.onnx --output_file nova_speech.wav
        cmd = [
            "piper",
            "--model", str(PIPER_MODEL_PATH),
            "--output_file", str(output_wav)
        ]
        
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        process.communicate(input=text.encode('utf-8'))
        
        if output_wav.exists():
            # Play using winsound or similar
            import winsound
            winsound.PlaySound(str(output_wav), winsound.SND_FILENAME)
            return True
    except Exception as e:
        print(f"Piper Error: {e}")
        return powershell_tts(text)
    return False

def powershell_tts(text):
    """Speak text using Windows PowerShell with female voice."""
    try:
        safe_text = text.replace('"', '').replace("'", "").replace('\n', ' ').replace('\r', ' ')
        cmd = f'''powershell -Command "Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $voices = $synth.GetInstalledVoices(); foreach($v in $voices) {{ if($v.VoiceInfo.Name -like '*Zira*') {{ $synth.SelectVoice($v.VoiceInfo.Name); break }} }}; $synth.Speak('{safe_text}');"'''
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

class VoiceWorker(QObject):
    """SimpliSmart Voice Assistant (Whisper STT + Wake Word)."""
    command_detected = pyqtSignal(str)
    status_changed = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.running = True
        self.model = None
        if WHISPER_AVAILABLE:
            try:
                # Load tiny model for speed and space efficiency
                # compute_type="int8" for less RAM/VRAM usage
                self.model = WhisperModel("tiny", device="cpu", compute_type="int8")
            except:
                pass

    def run(self):
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            recognizer.dynamic_energy_threshold = True
            
            with sr.Microphone() as source:
                self.status_changed.emit("CALIBRATING...", "#ffa500")
                recognizer.adjust_for_ambient_noise(source, duration=1)
                
                while self.running:
                    try:
                        self.status_changed.emit("AWAITING WAKE WORD", "#00d2ff")
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                        
                        # Use Whisper for higher accuracy if available
                        if self.model:
                            import io
                            wav_data = io.BytesIO(audio.get_wav_data())
                            segments, info = self.model.transcribe(wav_data, beam_size=1)
                            text = " ".join([segment.text for segment in segments]).lower().strip()
                        else:
                            text = recognizer.recognize_google(audio).lower()
                        
                        if "nova" in text or "hey nova" in text:
                            piper_tts("Yes, I'm here.")
                            self.status_changed.emit("LISTENING...", "#0f0")
                            cmd_audio = recognizer.listen(source, timeout=10, phrase_time_limit=15)
                            
                            if self.model:
                                wav_data = io.BytesIO(cmd_audio.get_wav_data())
                                segments, info = self.model.transcribe(wav_data, beam_size=5)
                                cmd_text = " ".join([segment.text for segment in segments]).strip()
                            else:
                                cmd_text = recognizer.recognize_google(cmd_audio)
                                
                            if cmd_text:
                                self.command_detected.emit(cmd_text)
                    except sr.WaitTimeoutError:
                        continue
                    except Exception as e:
                        print(f"STT Error: {e}")
                        continue
        except Exception as e:
            self.status_changed.emit("VOICE ERROR", "#ff4b2b")

class SimpliSmartInterface(QObject):
    """Bridge between JS HUD and Python API."""
    def __init__(self, window):
        super().__init__()
        self.window = window

    @pyqtSlot(str)
    def process_input(self, text):
        """Talk to Nova API /query."""
        threading.Thread(target=self._call_api, args=(text,), daemon=True).start()

    def _call_api(self, text):
        try:
            # Call local Nova API
            response = requests.post("http://localhost:5000/query", json={"query": text}, timeout=60)
            if response.status_code == 200:
                data = response.json()
                msg = data.get("response", "No response from Nova.")
                self.window.browser.page().runJavaScript(f"window.setNovaResponse({json.dumps(msg)})")
                piper_tts(msg)
            else:
                self.window.browser.page().runJavaScript(f"window.setNovaResponse('API Error: {response.status_code}')")
        except Exception as e:
            self.window.browser.page().runJavaScript(f"window.setNovaResponse('Connection Error: {str(e)}')")

    @pyqtSlot()
    def exit_app(self):
        os._exit(0)

    @pyqtSlot()
    def minimize_to_tray(self):
        self.window.hide()

class SimpliSmartWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1200, 800)
        
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)
        
        self.bridge = SimpliSmartInterface(self)
        self.channel = QWebChannel()
        self.channel.registerObject("pyObj", self.bridge)
        self.browser.page().setWebChannel(self.channel)
        
        hud_path = SCRIPT_DIR / "interface" / "nova_hud.html"
        self.browser.setUrl(QUrl.fromLocalFile(str(hud_path)))
        
        # Voice System
        self.voice_thread = QThread()
        self.voice_worker = VoiceWorker()
        self.voice_worker.moveToThread(self.voice_thread)
        self.voice_thread.started.connect(self.voice_worker.run)
        self.voice_worker.command_detected.connect(self.handle_voice_command)
        self.voice_worker.status_changed.connect(self.setStatus)
        self.voice_thread.start()

    def setStatus(self, status, color):
        self.browser.page().runJavaScript(f"window.setStatus({json.dumps(status)}, {json.dumps(color)})")

    def handle_voice_command(self, cmd):
        self.browser.page().runJavaScript(f"addMessage({json.dumps(cmd)}, 'user')")
        self.show()
        self.bridge.process_input(cmd)

def main():
    if not GUI_AVAILABLE:
        print("PyQt6 not found.")
        return
    app = QApplication(sys.argv)
    window = SimpliSmartWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
