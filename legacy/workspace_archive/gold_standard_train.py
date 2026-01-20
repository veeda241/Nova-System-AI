
import numpy as np
import json
import os
import sys
import random

# Ensure imports work from workspace root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine_core.model import TinyTransformerClassifier
from engine_core.tokenizer import SimpleWordTokenizer

def train_gold_standard():
    print("🚀 Initiating NIE Gold Standard Training (Precision Calibration)...", flush=True)
    tokenizer = SimpleWordTokenizer()
    try:
        with open("engine_training/dataset.json", "r") as f:
            raw_data = json.load(f)
    except:
        print("❌ Dataset not found.")
        return

    # 1. Dataset Balancing
    intent_bins = {i: [] for i in range(5)}
    for d in raw_data: intent_bins[d["label"]].append(d)
    max_samples = max(len(v) for v in intent_bins.values())
    balanced_data = []
    for bin_id in intent_bins:
        samples = intent_bins[bin_id]
        balanced_data.extend(samples * (max_samples // len(samples)) + samples[:max_samples % len(samples)])
    
    random.seed(42)
    np.random.seed(42)
    
    # 2. Model Setup
    model = TinyTransformerClassifier(vocab_size=1000)
    epochs = 300
    lr = 0.01 
    momentum = 0.9
    velocity = {k: np.zeros_like(v) for k, v in model.params.items()}
    
    print(f"📊 Balanced Dataset: {len(balanced_data)} samples | Strategy: Full-State SGD + Momentum", flush=True)
    
    for epoch in range(epochs):
        error_count = 0
        random.shuffle(balanced_data)
        
        for d in balanced_data:
            ids = tokenizer.encode(d["text"])
            target = d["label"]
            
            # --- FULL FORWARD PASS (To get 'pooled' state) ---
            seq_len = len(ids)
            h = model.params['w_tok'][ids] + model.params['w_pos'][:seq_len]
            for i in range(model.layers):
                q, k, v = h @ model.params[f'l{i}_wq'], h @ model.params[f'l{i}_wk'], h @ model.params[f'l{i}_wv']
                attn = model._softmax((q @ k.T) / np.sqrt(model.dim))
                h = h + (attn @ v) @ model.params[f'l{i}_wo']
                h = h + model._relu(h @ model.params[f'l{i}_w1']) @ model.params[f'l{i}_w2']
            pooled = np.mean(h, axis=0)
            
            logits = pooled @ model.params['w_final']
            probs = model._softmax(logits)
            
            if np.argmax(probs) != target: error_count += 1
            
            # --- GRADIENT CALCULATION ---
            grad_logits = probs.copy()
            grad_logits[target] -= 1
            
            # Classification Head Gradient
            g_w_final = np.outer(pooled, grad_logits)
            
            # CLIP GRADIENTS (Crucial for stability)
            g_w_final = np.clip(g_w_final, -1.0, 1.0)
            
            # Update Classification Head
            velocity['w_final'] = momentum * velocity['w_final'] - lr * g_w_final
            model.params['w_final'] += velocity['w_final']
            
            # Token Embedding Nudge (Aligning keywords with intent targets)
            target_vec = model.params['w_final'][:, target]
            for cid in ids:
                if cid != 0:
                    g_tok = (model.params['w_tok'][cid] - target_vec)
                    g_tok = np.clip(g_tok, -1.0, 1.0)
                    velocity['w_tok'][cid] = momentum * velocity['w_tok'][cid] - (lr * 0.1) * g_tok
                    model.params['w_tok'][cid] += velocity['w_tok'][cid]

        if epoch % 50 == 0:
            err = (error_count / len(balanced_data)) * 100
            print(f"   Epoch {epoch:3d} | Error Rate: {err:.1f}%", flush=True)
            if err < 0.5: break

    # 3. Finalization
    model.save("workspace/engine_core/model_weights.npz")
    with open("workspace/engine_core/vocab.json", "w") as f: json.dump(tokenizer.word_to_id, f)
    print("✅ NIE Precision Training Complete.")
    
    print("\n--- Final Verification ---")
    test_case = "lock the computer"
    final_probs = model.forward(tokenizer.encode(test_case))
    final_intent = np.argmax(final_probs)
    print(f"Input: '{test_case}' | Predicted: {final_intent} | Conf: {final_probs[final_intent]*100:.2f}%")

    # 5. Save Artifacts
    weights_path = "workspace/engine_core/model_weights.npz"
    vocab_path = "workspace/engine_core/vocab.json"
    model.save(weights_path)
    with open(vocab_path, "w") as f: json.dump(tokenizer.word_to_id, f)
    
    print(f"✅ Training Finalized. Weights saved to {weights_path}")
    print("--- Final Confidence Check ---")
    test_cmd = "lock the computer"
    probs = model.forward(tokenizer.encode(test_cmd))
    print(f"Test input: '{test_cmd}' | Intent: {np.argmax(probs)} | Confidence: {np.max(probs)*100:.2f}%")

if __name__ == "__main__":
    train_gold_standard()
