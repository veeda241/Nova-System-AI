
import sys
import os
import numpy as np
import json

# Ensure imports work from workspace root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine_core.model import TinyTransformerClassifier
from engine_core.tokenizer import SimpleWordTokenizer
from engine_interface.permission_gate import PermissionGate

class NeuralIntentEngine:
    """Main interface for the Neural Intent Engine (NIE)."""
    
    INTENTS = {
        0: "LOCK_SYSTEM",
        1: "VOLUME_UP",
        2: "VOLUME_DOWN",
        3: "SYSTEM_STATUS",
        4: "UNKNOWN"
    }
    
    def __init__(self, model_path="engine_core/model_weights.npz"):
        self.tokenizer = SimpleWordTokenizer()
        # Synchronized vocab_size with Gold Standard Training
        self.model = TinyTransformerClassifier(vocab_size=1000) 
        
        # Load Vocab if exists
        vocab_path = os.path.join("workspace", "engine_core", "vocab.json")
        if os.path.exists(vocab_path):
            with open(vocab_path, "r") as f:
                self.tokenizer.word_to_id = json.load(f)
                self.tokenizer.id_to_word = {i: w for w, i in self.tokenizer.word_to_id.items()}

        full_model_path = os.path.join("workspace", model_path)
        if os.path.exists(full_model_path):
            self.model.load(full_model_path)
            # Silencing prints for clean CLI integration
        else:
            pass

    def process_command(self, text):
        """Think about the command and return the detected intent and confidence."""
        # 1. Tokenize
        encoded = self.tokenizer.encode(text)
        
        # 2. Forward Pass
        probs = self.model.forward(encoded)
        intent_id = np.argmax(probs)
        confidence = probs[intent_id]
        
        intent_name = self.INTENTS.get(intent_id, "UNKNOWN")
        
        return {
            "intent_id": int(intent_id),
            "intent_name": intent_name,
            "confidence": float(confidence),
            "probs": probs.tolist()
        }

if __name__ == "__main__":
    engine = NeuralIntentEngine()
    def run_cmd(text):
        res = engine.process_command(text)
        print(f"\n🧠 Thinking... {res['intent_name']} ({res['confidence']*100:.1f}%)")
        if res['confidence'] >= 0.75 and res['intent_name'] != "UNKNOWN":
            if PermissionGate.ask_permission(res['intent_name'], res['confidence']):
                PermissionGate.execute_intent(res['intent_id'])
        else:
            print("❌ Low confidence or unknown intent.")

    if len(sys.argv) > 1:
        run_cmd(" ".join(sys.argv[1:]))
    else:
        while True:
            cmd = input("\nEnter laptop command (or 'exit'): ")
            if cmd.lower() in ['exit', 'quit']: break
            run_cmd(cmd)
