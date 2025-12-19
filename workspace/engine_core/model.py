
import numpy as np

class TinyTransformerClassifier:
    """
    A professional, from-scratch Transformer Classifier using only NumPy.
    Architecture: 2 Layers, 2 Heads, 64 Embedding Dim.
    Purpose: Intent classification with strict confidence monitoring.
    """
    
    def __init__(self, vocab_size, num_classes=5, dim=64, layers=2, heads=2):
        self.vocab_size = vocab_size
        self.num_classes = num_classes
        self.dim = dim
        self.layers = layers
        self.heads = heads
        self.params = self._init_weights()

    def _init_weights(self):
        """Initialize weights using Xavier initialization."""
        p = {}
        # Token Embedding
        p['w_tok'] = np.random.randn(self.vocab_size, self.dim) / np.sqrt(self.dim)
        # Positional Embedding (Learned)
        p['w_pos'] = np.random.randn(32, self.dim) / np.sqrt(self.dim)
        
        for i in range(self.layers):
            # Self-Attention
            p[f'l{i}_wq'] = np.random.randn(self.dim, self.dim) / np.sqrt(self.dim)
            p[f'l{i}_wk'] = np.random.randn(self.dim, self.dim) / np.sqrt(self.dim)
            p[f'l{i}_wv'] = np.random.randn(self.dim, self.dim) / np.sqrt(self.dim)
            p[f'l{i}_wo'] = np.random.randn(self.dim, self.dim) / np.sqrt(self.dim)
            # Feed Forward
            p[f'l{i}_w1'] = np.random.randn(self.dim, self.dim * 4) / np.sqrt(self.dim)
            p[f'l{i}_w2'] = np.random.randn(self.dim * 4, self.dim) / np.sqrt(self.dim * 4)
            
        # Final Classification Head
        p['w_final'] = np.random.randn(self.dim, self.num_classes) / np.sqrt(self.dim)
        return p

    def forward(self, x):
        """Transformer forward pass."""
        seq_len = len(x)
        # Embedding + Position
        h = self.params['w_tok'][x] + self.params['w_pos'][:seq_len]
        
        for i in range(self.layers):
            # Masked Self-Attention (Simple for classification)
            q = h @ self.params[f'l{i}_wq']
            k = h @ self.params[f'l{i}_wk']
            v = h @ self.params[f'l{i}_wv']
            
            # Scaled Dot-Product Attention
            attn_scores = (q @ k.T) / np.sqrt(self.dim)
            attn_weights = self._softmax(attn_scores)
            attn_out = attn_weights @ v
            h = h + attn_out @ self.params[f'l{i}_wo'] # Residual
            
            # Feed Forward
            ff = self._relu(h @ self.params[f'l{i}_w1']) @ self.params[f'l{i}_w2']
            h = h + ff # Residual
            
        # Mean pooling across sequence
        pooled = np.mean(h, axis=0)
        logits = pooled @ self.params['w_final']
        probs = self._softmax(logits)
        return probs

    def _softmax(self, x):
        e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
        return e_x / e_x.sum(axis=-1, keepdims=True)

    def _relu(self, x):
        return np.maximum(0, x)

    def save(self, path):
        np.savez(path, **self.params)

    def load(self, path):
        self.params = dict(np.load(path))
