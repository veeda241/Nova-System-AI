#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nova Orchestrator
=================
The central brain that routes queries based on intent.
"""

import os
import json
from typing import Dict, Any, Optional
from nova_system.intent_engine import IntentEngine
from nova_system.multi_model_brain import MultiModelBrain
from agent.claude_mcp_agent import ClaudeMCPAgent

class NovaOrchestrator:
    def __init__(self):
        self.intent_engine = IntentEngine()
        self.local_brain = MultiModelBrain() # Uses local Ollama default
        self.agent = ClaudeMCPAgent() # Support for Claude / Deep Logic
        
    def process_query(self, query: str) -> Dict[str, Any]:
        """Process a query through the architecture."""
        # 1. Classify Intent (Fast Local)
        intent_info = self.intent_engine.classify(query)
        intent = intent_info.get("intent", "CHAT")
        
        print(f"[*] Intent Detected: {intent} ({intent_info.get('confidence', 0)})")
        
        # 2. Route based on intent
        if intent in ["FILE_OPERATION", "CODE_GENERATION"]:
            # These require deep logic and tool access
            print("[*] Routing to Enhanced MCP Agent (Deep Logic)...")
            # We can use Claude here if configured in the agent
            response = self.agent.process_query(query)
            return {
                "response": response,
                "source": "Claude MCP / Enhanced Agent",
                "intent": intent
            }
            
        elif intent == "SYSTEM_COMMAND":
            print("[*] Routing to Linear Automation...")
            # We can use UCE or NeuralAuto here
            from nova_system.nova_neural_automation import NeuralAuto
            success, msg = NeuralAuto.execute_natural_language(query)
            return {
                "response": msg,
                "source": "Neural Automation",
                "intent": intent
            }
            
        else:
            # Casual chat or general knowledge
            print("[*] Routing to Local Brain...")
            response = self.local_brain.generate_response(query)
            return {
                "response": response,
                "source": "Local Brain",
                "intent": intent
            }

if __name__ == "__main__":
    orchestrator = NovaOrchestrator()
    print(orchestrator.process_query("Hello Nova!"))
    print(orchestrator.process_query("What files are in the current directory?"))
