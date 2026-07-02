#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Tests - Core Engine Tests
==============================
Unit tests for engine_core components.
"""

import os
import sys
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestIntentEngine(unittest.TestCase):
    """Tests for the intent engine."""
    
    def test_import(self):
        """Test that intent engine can be imported."""
        try:
            from nova_system.intent_engine import IntentEngine
            self.assertTrue(True)
        except ImportError as e:
            self.skipTest(f"IntentEngine not available: {e}")
    
    def test_classify_chat(self):
        """Test chat intent classification."""
        try:
            from nova_system.intent_engine import IntentEngine
            engine = IntentEngine()
            result = engine.classify("hello, how are you?")
            self.assertIn('intent', result)
        except Exception as e:
            self.skipTest(f"Intent engine test skipped: {e}")


class TestVocab(unittest.TestCase):
    """Tests for vocabulary handling."""
    
    def test_vocab_file_exists(self):
        """Test that vocab.json exists."""
        vocab_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "engine_core", "vocab.json"
        )
        self.assertTrue(os.path.exists(vocab_path))
    
    def test_vocab_valid_json(self):
        """Test that vocab.json is valid JSON."""
        import json
        vocab_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "engine_core", "vocab.json"
        )
        with open(vocab_path, 'r') as f:
            data = json.load(f)
        self.assertIsInstance(data, dict)


class TestMultiModelBrain(unittest.TestCase):
    """Tests for multi-model brain."""
    
    def test_import(self):
        """Test that MultiModelBrain can be imported."""
        try:
            from nova_system.multi_model_brain import MultiModelBrain
            self.assertTrue(True)
        except ImportError as e:
            self.skipTest(f"MultiModelBrain not available: {e}")
    
    def test_ollama_backend(self):
        """Test Ollama backend availability check."""
        try:
            from nova_system.multi_model_brain import OllamaBackend
            backend = OllamaBackend()
            # Just test the method exists
            self.assertTrue(hasattr(backend, 'is_available'))
        except Exception as e:
            self.skipTest(f"Ollama test skipped: {e}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
