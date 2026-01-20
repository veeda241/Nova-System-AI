#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Multi-Model AI Brain
===========================
A unified AI backend that automatically selects and uses the best available AI model.
Supports: Ollama (local), Groq (cloud), Gemini (cloud), OpenAI (cloud)

Priority Order:
1. Ollama (if running) - Free, private, local
2. Groq - Fast, free tier available
3. Gemini - Google's AI
4. OpenAI - Fallback
"""

import os
import json
import requests
from typing import Optional, Dict, List, Any
from abc import ABC, abstractmethod


class AIBackend(ABC):
    """Abstract base class for AI backends."""
    
    name: str = "base"
    priority: int = 100  # Lower = higher priority
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available."""
        pass
    
    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response."""
        pass
    
    def __repr__(self):
        return f"<{self.name} Backend>"


class OllamaBackend(AIBackend):
    """Local Ollama backend - runs on your machine."""
    
    name = "Ollama"
    priority = 1  # Highest priority (local, free, private)
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3"):
        self.base_url = base_url
        self.model = model
        self._available = None
        self._cached_model = None
    
    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get('models', [])
                if models:
                    # Find best model
                    model_names = [m['name'] for m in models]
                    preferred = ['llama3', 'llama3.2', 'mistral', 'gemma', 'qwen']
                    
                    for pref in preferred:
                        for m in model_names:
                            if pref in m.lower():
                                self._cached_model = m
                                break
                        if self._cached_model:
                            break
                    
                    if not self._cached_model and model_names:
                        self._cached_model = model_names[0]
                    
                    self._available = True
                    return True
        except:
            pass
        
        self._available = False
        return False
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.is_available():
            raise RuntimeError("Ollama not available")
        
        model = self._cached_model or self.model
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:"
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {"temperature": 0.7}
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json().get('response', '').strip()
            else:
                raise RuntimeError(f"Ollama error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama connection error: {e}")


class GroqBackend(AIBackend):
    """Groq cloud backend - fast inference."""
    
    name = "Groq"
    priority = 2
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('GROQ_API_KEY')
        self.model = "llama-3.3-70b-versatile"
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.is_available():
            raise RuntimeError("Groq API key not set")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 4096
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                raise RuntimeError(f"Groq error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Groq connection error: {e}")


class GeminiBackend(AIBackend):
    """Google Gemini backend."""
    
    name = "Gemini"
    priority = 3
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
        self.model = "gemini-1.5-flash"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.is_available():
            raise RuntimeError("Gemini API key not set")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            
            model = genai.GenerativeModel(self.model)
            
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            response = model.generate_content(full_prompt)
            return response.text
        except ImportError:
            # Use REST API fallback
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            response = requests.post(
                url,
                json={"contents": [{"parts": [{"text": full_prompt}]}]},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text']
            else:
                raise RuntimeError(f"Gemini error: {response.status_code}")


class OpenAIBackend(AIBackend):
    """OpenAI backend (GPT models)."""
    
    name = "OpenAI"
    priority = 4
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.model = "gpt-4o-mini"
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        if not self.is_available():
            raise RuntimeError("OpenAI API key not set")
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = requests.post(
                self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content']
            else:
                raise RuntimeError(f"OpenAI error: {response.status_code}")
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"OpenAI connection error: {e}")


class MultiModelBrain:
    """
    Unified multi-model AI brain.
    Automatically selects the best available AI backend.
    """
    
    def __init__(self):
        self.backends: List[AIBackend] = []
        self.active_backend: Optional[AIBackend] = None
        self._init_backends()
    
    def _init_backends(self):
        """Initialize all possible backends."""
        self.backends = [
            OllamaBackend(),
            GroqBackend(),
            GeminiBackend(),
            OpenAIBackend(),
        ]
        
        # Sort by priority
        self.backends.sort(key=lambda x: x.priority)
        
        # Find first available
        self._select_best_backend()
    
    def _select_best_backend(self):
        """Select the best available backend."""
        for backend in self.backends:
            # print(f"Checking {backend.name}...")
            if backend.is_available():
                self.active_backend = backend
                return
        
        self.active_backend = None
    
    def get_status(self) -> Dict:
        """Get status of all backends."""
        status = {
            "active": self.active_backend.name if self.active_backend else None,
            "backends": []
        }
        
        for backend in self.backends:
            status["backends"].append({
                "name": backend.name,
                "available": backend.is_available(),
                "priority": backend.priority
            })
        
        return status
    
    def is_available(self) -> bool:
        """Check if any backend is available."""
        return self.active_backend is not None
    
    @property
    def available(self) -> bool:
        """Backward compatibility property."""
        return self.is_available()
    
    def chat(self, message: str) -> str:
        """Simple chat interface (alias for generate_response)."""
        return self.generate_response(message)

    
    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response using the best available backend."""
        if not self.active_backend:
            self._select_best_backend()
        
        if not self.active_backend:
            return "Error: No AI backend available. Please set up Ollama, Groq, or Gemini."
        
        try:
            return self.active_backend.generate(prompt, system_prompt)
        except Exception as e:
            # Try fallback to next backend
            current_priority = self.active_backend.priority
            
            for backend in self.backends:
                if backend.priority > current_priority and backend.is_available():
                    try:
                        result = backend.generate(prompt, system_prompt)
                        self.active_backend = backend  # Switch to working backend
                        return result
                    except:
                        continue
            
            return f"Error: All AI backends failed. Last error: {e}"
    
    def switch_backend(self, name: str) -> bool:
        """Manually switch to a specific backend."""
        for backend in self.backends:
            if backend.name.lower() == name.lower():
                if backend.is_available():
                    self.active_backend = backend
                    return True
                else:
                    return False
        return False


# Alias for backward compatibility
NovaBrain = MultiModelBrain


def get_brain() -> MultiModelBrain:
    """Get or create the global brain instance."""
    global _brain_instance
    if '_brain_instance' not in globals():
        _brain_instance = MultiModelBrain()
    return _brain_instance


if __name__ == "__main__":
    brain = MultiModelBrain()
    print("Nova Multi-Model Brain Status:")
    print("-" * 40)
    
    status = brain.get_status()
    print(f"Active Backend: {status['active'] or 'NONE'}")
    print("\nAvailable Backends:")
    
    for b in status['backends']:
        icon = "✅" if b['available'] else "❌"
        print(f"  {icon} {b['name']} (Priority: {b['priority']})")
    
    if brain.is_available():
        print("\n" + "-" * 40)
        response = brain.generate_response("Say 'Hello, I am Nova!' in a friendly way.")
        print(f"Test Response: {response}")
