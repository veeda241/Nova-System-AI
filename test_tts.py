#!/usr/bin/env python3
"""Quick test for Nova Voice (TTS + STT)."""
import sys
sys.path.insert(0, '.')

print("=" * 50)
print("Nova Voice Quick Test")
print("=" * 50)

# Test 1: Check imports
print("\n[1] Checking imports...")
try:
    from nova_system.tts import SOPRANO_AVAILABLE, WHISPER_AVAILABLE
    print(f"  Soprano TTS: {'✅' if SOPRANO_AVAILABLE else '❌'}")
    print(f"  Whisper STT: {'✅' if WHISPER_AVAILABLE else '❌'}")
except ImportError as e:
    print(f"  ❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Initialize TTS only (not the full voice)
print("\n[2] Testing Soprano TTS...")
try:
    from nova_system.tts import NovaTTS
    tts = NovaTTS(device="cuda")
    print(f"  Provider: {tts.provider}")
    print(f"  Model loaded: {tts.soprano_model is not None}")
    
    if tts.soprano_model:
        print("  🔊 Speaking 'Hello sir'...")
        result = tts.speak("Hello sir, Nova at your service")
        print(f"  Result: {'✅' if result else '❌'}")
except Exception as e:
    print(f"  ❌ TTS error: {e}")

print("\n" + "=" * 50)
print("Test complete!")
