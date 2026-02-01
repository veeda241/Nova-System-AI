import requests
import json
import time
import sys

def test_api_status():
    print("[*] Testing Nova API Status...")
    try:
        response = requests.get("http://localhost:5000/status", timeout=5)
        if response.status_code == 200:
            print(f"✅ API Online: {response.json()}")
            return True
        else:
            print(f"❌ API returned status code {response.status_code}")
    except Exception as e:
        print(f"❌ Could not connect to API: {e}")
    return False

def test_intent_engine():
    print("\n[*] Testing Intent Engine...")
    from nova_system.intent_engine import IntentEngine
    engine = IntentEngine()
    test_query = "What time is it?"
    print(f"Query: '{test_query}'")
    try:
        result = engine.classify(test_query)
        print(f"✅ Classified as: {result.get('intent')} (Reason: {result.get('reason')})")
        return True
    except Exception as e:
        print(f"❌ Intent Engine failed: {e}")
    return False

def test_orchestrator():
    print("\n[*] Testing Orchestrator Routing...")
    from nova_system.workflow import NovaOrchestrator
    orch = NovaOrchestrator()
    queries = ["Hello!", "Open notepad", "Write a python script"]
    for q in queries:
        try:
            print(f"Processing: '{q}'")
            res = orch.process_query(q)
            print(f"✅ Response Source: {res.get('source')}")
        except Exception as e:
            print(f"❌ Orchestrator failed for '{q}': {e}")

if __name__ == "__main__":
    print("=== NOVA SYSTEM INTEGRATION TEST ===\n")
    # Note: API test requires the API to be running separately
    # test_api_status() 
    
    test_intent_engine()
    test_orchestrator()
