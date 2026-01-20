#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Groq Brain
================
Simple, fast LLM powered by Groq API.
No Ollama, no complexity - just Groq.
"""

import os
import json
import requests
from typing import Optional, List, Dict


class GroqBrain:
    """
    Nova's brain powered by Groq API.
    Fast inference with Llama 3.3 70B.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('GROQ_API_KEY')
        self.model = "llama-3.3-70b-versatile"
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.available = bool(self.api_key)
        self.conversation_history: List[Dict] = []
        
        if not self.available:
            print("⚠️ GROQ_API_KEY not found. Set it in .env or environment.")
    
    def is_available(self) -> bool:
        """Check if Groq is available."""
        return self.available
    
    def generate_response(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Generate a response using Groq API."""
        if not self.available:
            return "Error: Groq API key not set. Add GROQ_API_KEY to your .env file."
        
        messages = []
        
        # Add system prompt
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history (last 10 messages)
        messages.extend(self.conversation_history[-10:])
        
        # Add current user message
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
                    "max_tokens": 4096,
                    "top_p": 0.9
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                assistant_message = result['choices'][0]['message']['content']
                
                # Save to history
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append({"role": "assistant", "content": assistant_message})
                
                return assistant_message
            else:
                error_msg = response.json().get('error', {}).get('message', response.text)
                return f"Groq API Error: {error_msg}"
                
        except requests.exceptions.Timeout:
            return "Error: Groq request timed out. Please try again."
        except requests.exceptions.RequestException as e:
            return f"Error: Connection failed - {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def chat(self, message: str) -> str:
        """Simple chat interface."""
        return self.generate_response(message)
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def set_model(self, model: str):
        """Change the model."""
        valid_models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama-3.2-90b-vision-preview",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]
        if model in valid_models:
            self.model = model
            return True
        return False


# Alias for compatibility
NovaBrain = GroqBrain


# Quick test
if __name__ == "__main__":
    print("Testing Groq Brain...")
    print("-" * 40)
    
    brain = GroqBrain()
    
    if brain.is_available():
        print(f"✅ Groq API Connected")
        print(f"📦 Model: {brain.model}")
        print("-" * 40)
        
        response = brain.chat("Say 'Hello! I am Nova powered by Groq!' in a friendly way.")
        print(f"Response: {response}")
    else:
        print("❌ Groq API key not found")
        print("Set GROQ_API_KEY in your environment or .env file")
