#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════╗
║                 NOVA MULTI-MODEL VOICE ENGINE                 ║
║         Text-to-Speech & Speech-to-Text for Nova AI           ║
╠═══════════════════════════════════════════════════════════════╣
║  TTS Providers (in order of preference):                      ║
║    1. Edge TTS - Microsoft online female voice (Aria)         ║
║    2. Soprano (ekwek/Soprano-1.1-80M) - Neural, high quality  ║
║    3. pyttsx3 - Offline, fast, reliable (Zira female)         ║
║  STT Providers:                                               ║
║    1. Whisper - OpenAI offline speech recognition             ║
║    2. Google Speech - Online fallback                         ║
╚═══════════════════════════════════════════════════════════════╝
"""

import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional, List

# Set ffmpeg path for Whisper (from imageio-ffmpeg)
try:
    import imageio_ffmpeg
    os.environ["PATH"] = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe()) + os.pathsep + os.environ.get("PATH", "")
except ImportError:
    pass
# ═══════════════════════════════════════════════════════════════
#  AVAILABILITY FLAGS
# ═══════════════════════════════════════════════════════════════

SOPRANO_AVAILABLE = False
PYTTSX3_AVAILABLE = False
EDGE_TTS_AVAILABLE = False
WHISPER_AVAILABLE = False
SR_AVAILABLE = False

# Check Soprano
try:
    from soprano import SopranoTTS
    SOPRANO_AVAILABLE = True
except ImportError:
    pass

# Check pyttsx3 (reliable offline TTS)
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    pass

# Check Edge TTS
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
    # Pre-init pygame for faster TTS playback
    try:
        import pygame
        pygame.mixer.init()
    except:
        pass
except ImportError:
    pass

# Check Whisper
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    pass

# Check SpeechRecognition
try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    pass

# ═══════════════════════════════════════════════════════════════
#  NOVA VOICE SETTINGS
# ═══════════════════════════════════════════════════════════════

NOVA_VOICE_SETTINGS = {
    "greeting": "Hello sir, Nova at your service.",
    "ready": "Nova is ready to assist you, sir.",
    "thinking": "Processing your request, sir.",
    "error": "I encountered an issue. Let me try again, sir.",
    "goodbye": "Goodbye sir. Nova will be waiting.",
    "wake_response": "Yes sir?",
    "voice_mode_start": "Hello sir, Nova at your service.",
    "voice_mode_end": "Voice mode deactivated. Call me anytime, sir.",
}

# ═══════════════════════════════════════════════════════════════
#  MULTI-MODEL TTS ENGINE
# ═══════════════════════════════════════════════════════════════

class NovaTTS:
    """
    Multi-model TTS Engine with automatic fallback.
    
    Tries providers in order:
    1. Edge TTS (online, female neural voice - Aria)
    2. Soprano (neural, high quality)
    3. pyttsx3 (offline, fast fallback - Zira female)
    """
    
    # Female voice options
    EDGE_VOICE = "en-US-AriaNeural"  # Microsoft Aria - Female
    
    def __init__(self, device: str = "auto", timeout: int = 15):
        self.device = device
        self.timeout = timeout
        self.provider = None
        self.engine = None
        self.pyttsx3_engine = None  # Keep pyttsx3 as fallback
        self._init_best_provider()
    
    def _init_best_provider(self):
        """Initialize the best available TTS provider."""
        
        # Always init pyttsx3 as fallback first (female voice - Zira)
        if PYTTSX3_AVAILABLE:
            try:
                self.pyttsx3_engine = pyttsx3.init()
                voices = self.pyttsx3_engine.getProperty('voices')
                for voice in voices:
                    if 'zira' in voice.name.lower() or 'female' in voice.name.lower():
                        self.pyttsx3_engine.setProperty('voice', voice.id)
                        break
                self.pyttsx3_engine.setProperty('rate', 180)
                self.pyttsx3_engine.setProperty('volume', 1.0)
            except:
                self.pyttsx3_engine = None
        
        # Try Edge TTS first (online, high quality female voice)
        if EDGE_TTS_AVAILABLE:
            self.provider = "edge_tts"
            print(f"✅ TTS ready (Edge TTS - {self.EDGE_VOICE} female voice)")
            return
        
        # Try Soprano (neural)
        if SOPRANO_AVAILABLE:
            try:
                print("🔄 Loading Soprano TTS (ekwek/Soprano-1.1-80M)...")
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                self.engine = SopranoTTS(backend='auto', device=device)
                self.provider = "soprano"
                print(f"✅ TTS ready (Soprano neural voice - {device})")
                return
            except Exception as e:
                print(f"⚠️ Soprano failed: {e}")
        
        # Fallback to pyttsx3 (Zira female)
        if self.pyttsx3_engine:
            self.engine = self.pyttsx3_engine
            self.provider = "pyttsx3"
            print("✅ TTS ready (pyttsx3 - Zira female voice)")
            return
        
        print("⚠️ No TTS provider available")
        print("  Install one: pip install edge-tts")
    
    def speak(self, text: str, fast: bool = False) -> bool:
        """Speak text using the best available provider.
        
        Args:
            text: Text to speak
            fast: If True, use pyttsx3 for instant local speech
        """
        if not text or not text.strip():
            return False
        
        text = text.strip()
        
        # For short responses (<60 chars) or fast mode, use pyttsx3 (instant, local)
        if fast or len(text) < 60:
            if self.pyttsx3_engine:
                return self._speak_pyttsx3(text)
        
        if self.provider == "edge_tts":
            return self._speak_edge(text)
        elif self.provider == "pyttsx3":
            return self._speak_pyttsx3(text)
        elif self.provider == "soprano":
            return self._speak_soprano(text)
        
        print("⚠️ No TTS provider available")
        return False
    
    def _speak_pyttsx3(self, text: str) -> bool:
        """Speak using pyttsx3 (fast, offline)."""
        try:
            if self.pyttsx3_engine:
                self.pyttsx3_engine.say(text)
                self.pyttsx3_engine.runAndWait()
            else:
                self.engine.say(text)
                self.engine.runAndWait()
            return True
        except Exception as e:
            print(f"⚠️ pyttsx3 error: {e}")
            return False
    
    def _speak_soprano(self, text: str) -> bool:
        """Speak using Soprano with timeout and pyttsx3 fallback."""
        result = [False]
        
        def speak_thread():
            try:
                import sounddevice as sd
                # Soprano uses infer() to generate audio at 24000 Hz
                audio = self.engine.infer(text)
                # Play the audio at correct sample rate
                sd.play(audio, samplerate=24000)
                sd.wait()
                result[0] = True
            except Exception as e:
                print(f"⚠️ Soprano error: {e}")
        
        thread = threading.Thread(target=speak_thread, daemon=True)
        thread.start()
        thread.join(timeout=self.timeout)
        
        if thread.is_alive():
            print("⚠️ Soprano timeout, using pyttsx3 fallback...")
            # Fallback to pyttsx3
            if self.pyttsx3_engine:
                try:
                    self.pyttsx3_engine.say(text)
                    self.pyttsx3_engine.runAndWait()
                    return True
                except Exception as e:
                    print(f"⚠️ pyttsx3 fallback error: {e}")
            return False
        
        return result[0]
    
    def _speak_edge(self, text: str) -> bool:
        """Speak using Edge TTS (online, female voice)."""
        try:
            import asyncio
            import edge_tts
            import uuid
            
            # Use unique temp file to avoid permission issues
            mp3_path = os.path.join(tempfile.gettempdir(), f"nova_tts_{uuid.uuid4().hex[:8]}.mp3")
            
            async def generate():
                communicate = edge_tts.Communicate(text, self.EDGE_VOICE)
                await communicate.save(mp3_path)
            
            # Generate audio
            asyncio.run(generate())
            
            # Play audio using pygame
            try:
                import pygame
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.load(mp3_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                pygame.mixer.music.unload()
                # Cleanup temp file
                try:
                    os.remove(mp3_path)
                except:
                    pass
                return True
            except Exception as e:
                print(f"⚠️ pygame error: {e}")
            
            # Fallback: use Windows Media Player
            if os.name == 'nt':
                import subprocess
                subprocess.run(
                    ['powershell', '-c', f'(New-Object Media.SoundPlayer "{mp3_path}").PlaySync()'],
                    capture_output=True
                )
                try:
                    os.remove(mp3_path)
                except:
                    pass
                return True
            
            return False
            
        except Exception as e:
            print(f"⚠️ Edge TTS error: {e}")
            # Fallback to pyttsx3
            if self.pyttsx3_engine:
                try:
                    self.pyttsx3_engine.say(text)
                    self.pyttsx3_engine.runAndWait()
                    return True
                except:
                    pass
            return False


# ═══════════════════════════════════════════════════════════════
#  MULTI-MODEL STT ENGINE
# ═══════════════════════════════════════════════════════════════

class NovaSTT:
    """
    Multi-model STT Engine.
    
    Tries providers in order:
    1. Whisper (offline, accurate) - uses "tiny" for speed
    2. Google Speech (online fallback)
    """
    
    # Class-level model cache for instant reuse
    _whisper_cache = None
    
    def __init__(self, model_name: str = "tiny", preload: bool = True):
        self.model_name = model_name  # tiny is 5x faster than base
        self.whisper_model = None
        self.provider = None
        self._init_provider(preload=preload)
    
    def _init_provider(self, preload: bool = True):
        """Initialize STT provider."""
        if WHISPER_AVAILABLE:
            self.provider = "whisper"
            if preload:
                self._load_whisper()  # Pre-load for instant response
            else:
                print("✅ STT ready (Whisper tiny - offline)")
        elif SR_AVAILABLE:
            self.provider = "google"
            print("✅ STT ready (Google Speech - online)")
        else:
            print("⚠️ No STT provider available")
            print("  Install: pip install openai-whisper speechrecognition")
    
    def _load_whisper(self):
        """Load Whisper model (cached at class level for speed)."""
        if NovaSTT._whisper_cache is not None:
            self.whisper_model = NovaSTT._whisper_cache
            return self.whisper_model
            
        if self.whisper_model is None and WHISPER_AVAILABLE:
            print(f"🔄 Loading Whisper {self.model_name} model (one-time)...")
            import whisper
            self.whisper_model = whisper.load_model(self.model_name)
            NovaSTT._whisper_cache = self.whisper_model  # Cache for reuse
            print("✅ Whisper model loaded & cached")
        return self.whisper_model
    
    def listen(self, timeout: int = 5, phrase_time_limit: int = 15) -> Optional[str]:
        """Listen and transcribe speech."""
        if not SR_AVAILABLE:
            print("⚠️ Speech recognition not available")
            return None
        
        try:
            import speech_recognition as sr
            
            recognizer = sr.Recognizer()
            recognizer.dynamic_energy_threshold = True
            recognizer.energy_threshold = 300
            recognizer.pause_threshold = 0.8
            
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.2)
                print("🎤 Listening...")
                try:
                    audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                except sr.WaitTimeoutError:
                    print("⏰ No speech detected")
                    return None
            
            # Transcribe
            print("🔄 Processing...")
            
            if self.provider == "whisper" and WHISPER_AVAILABLE:
                return self._transcribe_whisper(audio)
            else:
                return self._transcribe_google(audio, recognizer)
                
        except Exception as e:
            print(f"❌ STT error: {e}")
            return None
    
    def _transcribe_whisper(self, audio) -> Optional[str]:
        """Transcribe using Whisper."""
        try:
            model = self._load_whisper()
            if not model:
                return self._transcribe_google(audio, None)
            
            # Save to temp file with proper Windows path
            import tempfile as tf
            temp_dir = tf.gettempdir()
            wav_path = os.path.join(temp_dir, "nova_whisper_input.wav")
            
            # Write audio data
            wav_data = audio.get_wav_data()
            with open(wav_path, "wb") as f:
                f.write(wav_data)
            
            # Verify file exists
            if not os.path.exists(wav_path):
                print(f"⚠️ Temp file not created: {wav_path}")
                return self._transcribe_google(audio, None)
            
            result = model.transcribe(wav_path, fp16=False)
            text = result.get("text", "").strip()
            
            # Cleanup temp file
            try:
                os.remove(wav_path)
            except:
                pass
            
            if text:
                print(f"✅ You said: {text}")
                return text.lower()
            return None
            
        except Exception as e:
            print(f"⚠️ Whisper error: {e}, trying Google...")
            return self._transcribe_google(audio, None)
    
    def _transcribe_google(self, audio, recognizer) -> Optional[str]:
        """Transcribe using Google Speech."""
        try:
            import speech_recognition as sr
            if recognizer is None:
                recognizer = sr.Recognizer()
            
            text = recognizer.recognize_google(audio, language='en-US')
            print(f"✅ You said: {text}")
            return text.lower()
        except sr.UnknownValueError:
            print("❓ Could not understand speech")
            return None
        except sr.RequestError as e:
            print(f"⚠️ Google Speech error: {e}")
            return None


# ═══════════════════════════════════════════════════════════════
#  NOVA VOICE - Unified Controller
# ═══════════════════════════════════════════════════════════════

_nova_voice: Optional["NovaVoice"] = None


class NovaVoice:
    """
    Nova AI Voice Controller - Unified TTS and STT.
    """
    
    def __init__(self, device: str = "auto"):
        print("\n🎙️ Initializing Nova Voice Engine...")
        self.tts = NovaTTS(device=device)
        self.stt = NovaSTT(model_name="tiny", preload=True)  # tiny=fast, preload=instant
        self.enabled = True
        self.muted = False
        print("✅ Nova Voice Engine ready!\n")
    
    def say(self, text: str) -> bool:
        """Speak text as Nova."""
        if not self.enabled or self.muted:
            return False
        return self.tts.speak(text)
    
    def listen(self, timeout: int = 5) -> Optional[str]:
        """Listen for speech."""
        return self.stt.listen(timeout=timeout)
    
    def greet(self) -> bool:
        """Nova greeting."""
        return self.say(NOVA_VOICE_SETTINGS["greeting"])
    
    def ready(self) -> bool:
        """Announce Nova is ready."""
        return self.say(NOVA_VOICE_SETTINGS["ready"])
    
    def thinking(self) -> bool:
        """Announce processing."""
        return self.say(NOVA_VOICE_SETTINGS["thinking"])
    
    def goodbye(self) -> bool:
        """Nova goodbye."""
        return self.say(NOVA_VOICE_SETTINGS["goodbye"])
    
    def mute(self):
        """Mute Nova."""
        self.muted = True
    
    def unmute(self):
        """Unmute Nova."""
        self.muted = False
    
    def toggle(self) -> bool:
        """Toggle voice."""
        self.enabled = not self.enabled
        return self.enabled


def get_nova_voice(device: str = "auto") -> NovaVoice:
    """Get or create Nova voice singleton."""
    global _nova_voice
    if _nova_voice is None:
        _nova_voice = NovaVoice(device=device)
    return _nova_voice


def nova_say(text: str) -> bool:
    """Quick speak function."""
    return get_nova_voice().say(text)


def nova_listen(timeout: int = 5) -> Optional[str]:
    """Listen for speech."""
    return get_nova_voice().listen(timeout=timeout)


def nova_greet() -> bool:
    """Nova greeting."""
    return get_nova_voice().greet()


# ═══════════════════════════════════════════════════════════════
#  TEST
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 50)
    print("Nova Voice Engine Test")
    print("=" * 50)
    
    print(f"\nAvailable providers:")
    print(f"  Soprano TTS: {'✅' if SOPRANO_AVAILABLE else '❌'}")
    print(f"  pyttsx3 TTS: {'✅' if PYTTSX3_AVAILABLE else '❌'}")
    print(f"  Edge TTS:    {'✅' if EDGE_TTS_AVAILABLE else '❌'}")
    print(f"  Whisper STT: {'✅' if WHISPER_AVAILABLE else '❌'}")
    print(f"  Google STT:  {'✅' if SR_AVAILABLE else '❌'}")
    
    print("\n" + "=" * 50)
    voice = get_nova_voice()
    
    print("\nTesting TTS...")
    voice.say("Hello sir, Nova voice engine is working.")
    
    print("\nDone!")
