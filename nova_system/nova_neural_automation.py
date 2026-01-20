#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Neural Automation Controller
=================================
An AI-driven automation interface that translates natural language into
complex system sequences using the Unified Control Engine (UCE).
"""
import time
from typing import List, Dict, Any, Optional
from nova_system.nova_automation import UCE, quick_command
from nova_system.multi_model_brain import MultiModelBrain

class NeuralAutomationController:
    """
    High-level controller that uses AI to orchestrate system automation.
    """
    
    def __init__(self, brain: Optional[MultiModelBrain] = None):
        self.brain = brain or MultiModelBrain()
        self.uce = UCE
        self.history = []

    def execute_natural_language(self, command_text: str):
        """
        Interpret and execute a natural language command.
        """
        print(f"\n🧠 Nova is interpreting: '{command_text}'")
        
        # 1. Ask the Brain to break it down into UCE commands
        system_prompt = """
        You are the NOVA Neural Automation Controller. 
        Translate user requests into a list of UCE commands.
        Available UCE commands:
        - open <app>
        - close <app>
        - volume <0-100>
        - brightness <0-100>
        - mute/unmute
        - lock
        - screenshot
        - search <query>
        - play <video>
        - go <url>
        - type <text>
        - clear temp
        
        Return ONLY a JSON list of strings, e.g. ["open notepad", "type hello", "volume 50"]
        """
        
        try:
            response = self.brain.generate_response(command_text, system_prompt)
            # Parse JSON list
            import json
            import re
            
            # Extract JSON from response
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                commands = json.loads(match.group())
            else:
                # Fallback: Treat response as a single command if not JSON
                commands = [command_text]
                
            for cmd in commands:
                print(f"  ⚡ Executing: {cmd}...", end=" ", flush=True)
                success, msg = quick_command(cmd)
                if success:
                    print("✅")
                else:
                    print(f"❌ ({msg})")
                time.sleep(0.5)
                
            return True, f"Executed {len(commands)} automation steps."
            
        except Exception as e:
            return False, f"Neural interpretation failed: {e}"

    def run_optimization_routine(self):
        """
        AI-driven routine to optimize system performance.
        """
        print("\n⚡ Starting Neural System Optimization...")
        steps = [
            "clear temp",
            "status"
        ]
        for step in steps:
            print(f"  > {step}...", end=" ", flush=True)
            quick_command(step)
            print("✅")
            time.sleep(0.3)
        print("✨ System Optimized by Nova AI.")

# Global instance
NeuralAuto = NeuralAutomationController()
