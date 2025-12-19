
import numpy as np
import json
import os
import sys
import random

# Ensure imports work from workspace root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine_core.model import TinyTransformerClassifier
from engine_core.tokenizer import SimpleWordTokenizer

def train():
    # 1. Load Data
    with open("engine_training/dataset.json", "r") as f:
        data = json.load(f)
    
    tokenizer = SimpleWordTokenizer()
    # 2. Init Model with stable vocab size
    model = TinyTransformerClassifier(vocab_size=500) 
    
    # 3. Training Loop (SGD)
    epochs = 100
    lr = 0.5
    
    print(f"🚀 Training Neural Intent Engine (Prototype Alignment) on {len(data)} samples...", flush=True)
    
    for epoch in range(epochs):
        epoch_loss = 0
        random.shuffle(data)
        
        for d in data:
            ids = tokenizer.encode(d["text"])
            target = d["label"]
            
            # 1. Forward pass (for diagnostic info)
            probs = model.forward(ids)
            pred = np.argmax(probs)
            
            # 2. PROTOTYPE ALIGNMENT
            # Simplified: Update the weights so that the sum of token embeddings 
            # for this command aligns with the target classification row.
            
            # Get mean embedding of the current input (Representative Feature)
            # We ignore the attention layers during this alignment step for stability
            h_input = np.mean(model.params['w_tok'][ids], axis=0)
            
            # Nudge the target classification vector towards the input features
            model.params['w_final'][:, target] = (1 - lr*0.1) * model.params['w_final'][:, target] + (lr*0.1) * h_input
            
            # Nudge the specific tokens used in this command towards the intent centroid
            target_centroid = model.params['w_final'][:, target]
            for char_id in ids:
                if char_id != 0:
                    model.params['w_tok'][char_id] += lr * 0.05 * (target_centroid - model.params['w_tok'][char_id])

            if pred != target:
                epoch_loss += 1
                    
        if epoch % 10 == 0:
            error_rate = (epoch_loss / len(data)) * 100
            print(f"   Epoch {epoch}: Error Rate {error_rate:.1f}%", flush=True)
            if error_rate < 0.5: break

    # 4. Save
    model.save("workspace/engine_core/model_weights.npz")
    print("✅ Training complete. Model saved.", flush=True)

if __name__ == "__main__":
    train()
