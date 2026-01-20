import os
import sys
import time
from datetime import datetime

# Add root to sys.path
root = os.path.dirname(os.path.abspath(__file__))
if root not in sys.path:
    sys.path.append(root)

print("🔍 NOVA SYSTEM SELF-TEST & OPTIMIZATION")
print("========================================")

def test_component(name, import_func):
    print(f"Testing {name:20} ... ", end="", flush=True)
    try:
        import_func()
        print("✅ OK")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        return False

# 1. Test Packages
print("\n[1] Checking Packages:")
results = []
results.append(test_component("nova_system", lambda: __import__("nova_system")))
results.append(test_component("agent", lambda: __import__("agent")))

# 2. Test Brains
print("\n[2] Checking Brains:")
def check_groq():
    from nova_system.groq_brain import GroqBrain
    b = GroqBrain()
    if not b.is_available(): raise Exception("Groq API key missing")

def check_multi():
    from nova_system.multi_model_brain import MultiModelBrain
    b = MultiModelBrain()
    print(f" (Active: {b.active_brain})", end="")

results.append(test_component("Groq Brain", check_groq))
results.append(test_component("Multi-Model Brain", check_multi))

# 3. Test Agent
print("\n[3] Checking Agents:")
def check_agent():
    from nova_system.nova_agent import NovaAutonomousAgent
    from nova_system.groq_brain import GroqBrain
    a = NovaAutonomousAgent(GroqBrain())

results.append(test_component("Autonomous Agent", check_agent))

# 4. Test Automation
print("\n[4] Checking Automation:")
def check_auto():
    from nova_system.nova_automation import UCE
    status = UCE.get_status()
    print(f" (Engines: {len(status['engines'])})", end="")

results.append(test_component("Automation Engine", check_auto))

# 5. Test Voice
print("\n[5] Checking Voice:")
def check_sr():
    import speech_recognition as sr
def check_pyaudio():
    import pyaudio

test_component("SpeechRecognition", check_sr)
test_component("PyAudio", check_pyaudio)

print("\n========================================")
score = results.count(True)
total = len(results)
print(f"SCORE: {score}/{total}")

if score == total:
    print("🚀 NOVA IS FULLY EVOLVED AND READY FOR DEPLOYMENT!")
else:
    print("⚠️  SOME COMPONENTS NEED ATTENTION.")
