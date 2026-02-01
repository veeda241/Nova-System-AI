"""Test script for Nova Voice (Soprano TTS + Whisper STT)."""
import sys
sys.path.insert(0, '.')

print("=" * 50)
print("Nova Voice Test (Soprano TTS + Whisper STT)")
print("=" * 50)

# Test imports
print("\n[1] Testing imports...")
try:
    from nova_system.tts import (
        NovaTTS, NovaSTT, NovaVoice, 
        get_nova_voice, nova_say, nova_listen,
        SOPRANO_AVAILABLE
    )
    print(f"  ✅ TTS module imported")
    print(f"  ✅ Soprano available: {SOPRANO_AVAILABLE}")
except ImportError as e:
    print(f"  ❌ Import error: {e}")
    sys.exit(1)

# Test TTS
print("\n[2] Testing Soprano TTS...")
try:
    tts = NovaTTS(device="auto")
    print(f"  ✅ TTS initialized on device: {tts.device}")
    
    # Test speech
    print("  🔊 Speaking: 'Nova voice test successful'...")
    result = tts.speak("Nova voice test successful")
    if result:
        print("  ✅ TTS speech completed")
    else:
        print("  ⚠️ TTS returned False (may have timed out)")
except Exception as e:
    print(f"  ❌ TTS error: {e}")

# Test STT
print("\n[3] Testing Whisper STT...")
try:
    stt = NovaSTT()
    print(f"  ✅ STT initialized (Whisper)")
    print("  ℹ️ Whisper model will load on first use")
except Exception as e:
    print(f"  ❌ STT error: {e}")

# Test unified voice
print("\n[4] Testing NovaVoice (unified controller)...")
try:
    voice = get_nova_voice(device="auto")
    print(f"  ✅ NovaVoice created")
    print(f"  ✅ TTS ready: {voice.tts is not None}")
    print(f"  ✅ STT ready: {voice.stt is not None}")
except Exception as e:
    print(f"  ❌ Voice error: {e}")

# Test CLI integration
print("\n[5] Testing CLI VoiceControl...")
try:
    from interface.cli import VoiceControl, NOVA_VOICE_AVAILABLE
    print(f"  ✅ VoiceControl imported")
    print(f"  ✅ Nova Voice available: {NOVA_VOICE_AVAILABLE}")
except Exception as e:
    print(f"  ❌ CLI error: {e}")

print("\n" + "=" * 50)
print("✅ All tests completed!")
print("=" * 50)
print("\nTo test voice commands, run: python interface/cli.py")
print("Then type: /voice on")
print("And speak: 'nova hello'")
