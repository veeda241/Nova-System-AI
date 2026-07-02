#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nova Intent Engine (Fast Local)
===============================
Uses a tiny, fast LLM (e.g., Qwen2.5-0.5B) to classify user intent.
"""

import json
import requests
from typing import Dict, Any, Optional

class IntentEngine:
    def __init__(self, model: str = "qwen2.5:0.5b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.intents = {
            "CHAT": "Casual conversation, greetings, or general questions.",
            "SYSTEM_COMMAND": "Requests to open apps, change volume, lock PC, etc.",
            "FILE_OPERATION": "Requests to read, write, delete, or search for files.",
            "CODE_GENERATION": "Requests to write code, scripts, or debug software.",
            "KNOWLEDGE_SEARCH": "Deep research questions requiring broad knowledge.",
            "MEDIA_CONTROL": "Play music, YouTube videos, or control media playback."
        }

    def classify(self, text: str) -> Dict[str, Any]:
        """Classify the user intent using local Ollama."""
        system_prompt = f"""
        You are an Intent Classification Engine. Categorize the user's request into EXACTLY ONE of these categories:
        {json.dumps(self.intents, indent=2)}

        Return ONLY a JSON object: {{"intent": "CATEGORY", "confidence": 0.0-1.0, "reason": "short explanation"}}
        """
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"User Request: {text}",
                    "system": system_prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json().get('response', '{}')
                return json.loads(result)
            return {"intent": "CHAT", "confidence": 0.5, "error": "Ollama error"}
        except Exception as e:
            return {"intent": "CHAT", "confidence": 0.5, "error": str(e)}

if __name__ == "__main__":
    engine = IntentEngine()
    test_queries = [
        "What time is it?",
        "Open notepad and type hello world",
        "Write a python script to web scrape google",
        "How are you today?"
    ]
    for q in test_queries:
        print(f"Query: {q} -> {engine.classify(q)}")
