
import sys
import os
import numpy as np

# Ensure imports work from workspace root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine_core.model import TinyTransformerClassifier
from engine_core.tokenizer import SimpleWordTokenizer

def check():
    print("NIE Health Check...")
    tokenizer = SimpleWordTokenizer()
    model = TinyTransformerClassifier(vocab_size=1000)
    
    text = "lock the computer"
    ids = tokenizer.encode(text)
    print(f"Text: {text} | IDs: {ids}")
    
    probs = model.forward(ids)
    print(f"Probabilities: {probs}")
    print(f"Prediction: {np.argmax(probs)}")
    print("Health Check PASSED.")

if __name__ == "__main__":
    check()
