try:
    import speech_recognition as sr
    print(f"✅ speech_recognition imported. Version: {sr.__version__}")
    try:
        r = sr.Recognizer()
        print("✅ Recognizer initialized.")
    except Exception as e:
        print(f"❌ Failed to initialize Recognizer: {e}")
except ImportError as e:
    print(f"❌ Failed to import speech_recognition: {e}")
except Exception as e:
    print(f"❌ Unexpected error importing speech_recognition: {e}")

try:
    import pyaudio
    print("✅ pyaudio imported.")
except ImportError as e:
    print(f"❌ Failed to import pyaudio: {e}")
except Exception as e:
    print(f"❌ Unexpected error importing pyaudio: {e}")
