
import json
import os
import re

class SimpleWordTokenizer:
    """Professional word-level tokenizer for the Neural Intent Engine."""
    
    def __init__(self, vocab_path="engine_core/vocab.json"):
        self.vocab_path = vocab_path
        self.word_to_id = {"[PAD]": 0, "[UNK]": 1}
        self.id_to_word = {0: "[PAD]", 1: "[UNK]"}
        self.vocab_size = 2
        
        # Pre-populate with typical command words for better stability
        standard_words = [
            "lock", "computer", "system", "status", "volume", "up", "down", 
            "increase", "decrease", "make", "quieter", "louder", "check", 
            "laptop", "screen", "machine", "battery", "cpu", "usage"
        ]
        for word in standard_words:
            self._add_word(word)

    def _add_word(self, word):
        if word not in self.word_to_id:
            self.word_to_id[word] = self.vocab_size
            self.id_to_word[self.vocab_size] = word
            self.vocab_size += 1

    def _save_vocab(self):
        os.makedirs(os.path.dirname(self.vocab_path), exist_ok=True)
        with open(self.vocab_path, "w") as f:
            json.dump(self.word_to_id, f)

    def encode(self, text, max_len=12):
        """Convert text to list of word IDs, padded to max_len."""
        text = text.lower().strip()
        # Simple regex tokenizer
        words = re.findall(r'\w+', text)
        ids = []
        for w in words[:max_len]:
            if w not in self.word_to_id:
                self._add_word(w)
            ids.append(self.word_to_id[w])
            
        padding = [0] * (max_len - len(ids))
        return ids + padding

    def decode(self, ids):
        """Convert list of word IDs back to text."""
        return " ".join([self.id_to_word.get(i, "[UNK]") for i in ids if i != 0])
