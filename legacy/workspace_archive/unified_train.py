
import numpy as np
import json
import os
import re
import random

# ==========================================
# 🧠 NEURAL INTENT ENGINE - UNIFIED CORE
# ==========================================

class SimpleWordTokenizer:
    def __init__(self):
        self.word_to_id = {"[PAD]": 0, "[UNK]": 1}
        self.id_to_word = {0: "[PAD]", 1: "[UNK]"}
        self.vocab_size = 2
        for word in ["lock", "computer", "system", "status", "volume", "up", "down", "check"]:
            self._add_word(word)

    def _add_word(self, word):
        if word not in self.word_to_id:
            self.word_to_id[word] = self.vocab_size
            self.id_to_word[self.vocab_size] = word
            self.vocab_size += 1

    def encode(self, text, max_len=12):
        words = re.findall(r'\w+', text.lower())
        ids = []
        for w in words[:max_len]:
            if w not in self.word_to_id: self._add_word(w)
            ids.append(self.word_to_id[w])
        return ids + [0] * (max_len - len(ids))

class TinyTransformer:
    def __init__(self, vocab_size, num_classes=5, dim=64):
        self.dim = dim
        self.num_classes = num_classes
        self.params = {
            'w_tok': np.random.randn(vocab_size, dim) / np.sqrt(dim),
            'w_final': np.random.randn(dim, num_classes) / np.sqrt(dim)
        }

    def forward(self, x):
        # Feature Extraction: Mean of Token Embeddings
        h = np.mean(self.params['w_tok'][x], axis=0)
        logits = h @ self.params['w_final']
        # Softmax
        ex = np.exp(logits - np.max(logits))
        return ex / ex.sum()

def train_brain():
    print("🚀 Starting Professional NIE Training (Unified Core)...", flush=True)
    
    # 1. Load Dataset
    try:
        with open("engine_training/dataset.json", "r") as f:
            data = json.load(f)
    except:
        print("❌ Dataset not found at engine_training/dataset.json")
        return

    tokenizer = SimpleWordTokenizer()
    # Pre-train tokenizer to lock vocab
    for d in data: tokenizer.encode(d["text"])
    
    model = TinyTransformer(vocab_size=tokenizer.vocab_size)
    
    epochs = 100
    lr = 1.0
    
    for epoch in range(epochs):
        epoch_loss = 0
        random.shuffle(data)
        for d in data:
            ids = tokenizer.encode(d["text"])
            target = d["label"]
            
            probs = model.forward(ids)
            pred = np.argmax(probs)
            
            if pred != target or probs[target] < 0.95:
                # Direct Reinforcement: Move embeddings and classifier head toward each other
                h_input = np.mean(model.params['w_tok'][ids], axis=0)
                model.params['w_final'][:, target] += lr * 0.1 * h_input
                model.params['w_final'][:, pred] -= lr * 0.05 * h_input
                
                target_vec = model.params['w_final'][:, target]
                for cid in ids:
                    if cid != 0:
                        model.params['w_tok'][cid] += lr * 0.05 * (target_vec - model.params['w_tok'][cid])
                
                epoch_loss += 1
        
        if epoch % 20 == 0:
            print(f"   Epoch {epoch}: Error Rate {(epoch_loss/len(data))*100:.1f}%", flush=True)
            if epoch_loss == 0: break

    # Save
    weights_path = "workspace/engine_core/model_weights.npz"
    vocab_path = "workspace/engine_core/vocab.json"
    np.savez(weights_path, **model.params)
    with open(vocab_path, "w") as f: json.dump(tokenizer.word_to_id, f)
    print(f"✅ Training complete. Weights saved to {weights_path}")

if __name__ == "__main__":
    train_brain()
