
import sys
import os
import numpy as np

# Ensure imports work from workspace root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine_core.model import TinyTransformerClassifier
from engine_core.tokenizer import CharTokenizer

def diagnostic():
    tokenizer = CharTokenizer()
    model = TinyTransformerClassifier(vocab_size=tokenizer.vocab_size)
    
    weights_path = "workspace/engine_core/model_weights.npz"
    if not os.path.exists(weights_path):
        print(f"❌ No weights found at {weights_path}")
        return

    model.load(weights_path)
    print("✅ Model Weights Loaded.")

    test_cases = [
        "lock the computer",
        "increase volume",
        "volume up",
        "make it quiet",
        "system status",
        "how is the battery",
        "hello",
        "what time is it"
    ]

    INTENTS = {0: "LOCK_SYSTEM", 1: "VOLUME_UP", 2: "VOLUME_DOWN", 3: "SYSTEM_STATUS", 4: "UNKNOWN"}

    print("\n--- Model Diagnostic Results ---")
    for text in test_cases:
        encoded = tokenizer.encode(text)
        probs = model.forward(encoded)
        intent_id = np.argmax(probs)
        conf = probs[intent_id]
        
        print(f"Text: '{text}'")
        print(f"  Prediction: {INTENTS[intent_id]} ({intent_id})")
        print(f"  Confidence: {conf*100:.2f}%")
        print(f"  Raw: {probs}")

if __name__ == "__main__":
    diagnostic()
