#!/usr/bin/env python3
"""Test STT (Speech-to-Text) with OpenAI Whisper."""

import speech_recognition as sr
import tempfile
from pathlib import Path

def test_listen():
    r = sr.Recognizer()
    print("🎤 Nova STT Test (Whisper)")
    print("=" * 40)
    print("Speak now! (5 second timeout)")
    print()
    
    with sr.Microphone() as source:
        # Calibrate for background noise
        print("🔇 Calibrating for ambient noise...")
        r.adjust_for_ambient_noise(source, duration=1.0)
        print("✅ Calibration done.")
        print()
        print("🔊 Listening... Speak now!")
        
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=10)
            print("🔄 Processing with Whisper...")
            
            # Use Whisper for transcription
            try:
                import whisper
                
                # Save audio to temp file
                wav_path = str(Path(tempfile.gettempdir()) / "nova_whisper_test.wav")
                with open(wav_path, "wb") as f:
                    f.write(audio.get_wav_data())
                
                # Load Whisper model and transcribe
                print("📦 Loading Whisper base model...")
                model = whisper.load_model("base")
                result = model.transcribe(wav_path, fp16=False)
                text = result.get("text", "").strip()
                
                if text:
                    print(f"\n✅ You said: \"{text}\"")
                    return text
                else:
                    print("\n❌ Could not understand speech")
                    return None
                    
            except ImportError:
                print("\n⚠️ Whisper not installed. Install with: pip install openai-whisper")
                return None
                
        except sr.WaitTimeoutError:
            print("\n❌ No speech detected (timeout)")
            print("   - Try speaking louder")
            print("   - Make sure microphone is not muted")
            return None
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return None

if __name__ == "__main__":
    test_listen()
