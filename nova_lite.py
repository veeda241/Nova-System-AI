#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Core Assistant (Unified Edition)
======================================
A clean, modular "Core" that serves as the foundation for the Nova AI Assistant.

This module can be:
1. Run STANDALONE as a simple text-based assistant (`python nova_lite.py`)
2. IMPORTED by `nova_cli.py` to provide the core processing engine
3. Used with `nova_server.py` for a web-based GUI

Architecture:
- IntentClassifier: Hybrid Rule-Based + Generative NLP
- CommandRouter: Executes system commands (apps, volume, web, etc.)
- PluginSystem: Easily extend with new features
- Brain: LLM integration via Groq/Gemini/Ollama

This is the "Text-Only Assistant" you envisioned, now integrated with Nova.
"""

import os
import sys
import json
import re
import subprocess
import random
from typing import Optional, Dict, List, Any, Callable
from datetime import datetime

# ============================================================================
# IMPORTS - Gracefully handle missing modules
# ============================================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

# Brain (LLM)
GroqBrain = None
try:
    from nova_system.groq_brain import GroqBrain
except ImportError:
    pass

# Multi-Model Brain (with failover)
MultiModelBrain = None
try:
    from nova_system.multi_model_brain import MultiModelBrain
except ImportError:
    pass

# Automation Layers
AppControlLayer = None
SystemInteractionEngine = None
WebControlLayer = None
try:
    from nova_system.nova_automation import AppControlLayer, SystemInteractionEngine, WebControlLayer
except ImportError:
    pass

# AppFinder for smart app discovery
AppFinder = None
try:
    # Try to import from the main nova_cli if available
    from nova_cli import AppFinder, APP_FINDER
except ImportError:
    APP_FINDER = None

# ============================================================================
# INTENT CLASSIFIER - Hybrid NLP Engine
# ============================================================================
class IntentClassifier:
    """
    Handles intent recognition using a hybrid approach:
    1. Keyword/Regex matching for "obvious" commands (fast, offline)
    2. LLM-based classification for complex queries (smart, online)
    """
    
    def __init__(self, brain=None):
        self.brain = brain
        
        # Define intents with their trigger patterns (regex)
        self.intents = {
            # App Control
            'open_app': [
                r'^open\s+(.+)$', r'^start\s+(.+)$', r'^launch\s+(.+)$',
                r'^run\s+(.+)$', r'^execute\s+(.+)$'
            ],
            'close_app': [
                r'^close\s+(.+)$', r'^exit\s+(.+)$', r'^stop\s+(.+)$',
                r'^kill\s+(.+)$', r'^terminate\s+(.+)$'
            ],
            
            # Web Actions
            'search_web': [
                r'^(?:google\s+)?search\s+(?:for\s+)?(.+)$',
                r'^google\s+(.+)$', r'^lookup\s+(.+)$', r'^find\s+(.+)$'
            ],
            'play_video': [
                r'^play\s+(.+)$', r'^youtube\s+(.+)$',
                r'^watch\s+(.+)$', r'^stream\s+(.+)$'
            ],
            'open_url': [
                r'^(?:go to|open|visit|browse)\s+(https?://\S+)$',
                r'^(https?://\S+)$'
            ],
            
            # System Control
            'set_volume': [r'^(?:set\s+)?volume\s+(?:to\s+)?(\d+)$', r'^volume\s+(\d+)$'],
            'set_brightness': [r'^(?:set\s+)?brightness\s+(?:to\s+)?(\d+)$'],
            'mute': [r'^mute$', r'^mute\s+volume$', r'^silence$'],
            'unmute': [r'^unmute$', r'^unmute\s+volume$'],
            'lock': [r'^lock$', r'^lock\s+screen$', r'^lock\s+computer$'],
            'shutdown': [r'^shutdown$', r'^shutdown\s+computer$', r'^turn\s+off$'],
            'restart': [r'^restart$', r'^reboot$', r'^restart\s+computer$'],
            
            # System Status
            'system_status': [
                r'^system\s+status$', r'^status$', r'^system\s+info$',
                r'^cpu\s+usage$', r'^memory\s+usage$', r'^disk\s+usage$'
            ],
            'battery_status': [r'^battery$', r'^battery\s+status$', r'^power$'],
            'time': [r'^(?:what\s+)?time$', r'^(?:what\s+is\s+the\s+)?time$', r'^clock$'],
            'date': [r'^(?:what\s+)?date$', r'^(?:what\s+is\s+the\s+)?date$', r'^today$'],
            
            # Conversation
            'greeting': [
                r'^(?:hello|hi|hey|good\s+morning|good\s+afternoon|good\s+evening)$',
                r'^(?:hello|hi|hey)\s+nova$'
            ],
            'farewell': [r'^(?:bye|goodbye|see\s+you|exit|quit)$'],
            'thanks': [r'^(?:thank|thanks|thank\s+you)'],
            'help': [r'^help$', r'^(?:what\s+can\s+you\s+do)$', r'^commands$'],
            
            # Fun
            'joke': [r'^(?:tell\s+me\s+a\s+)?joke$', r'^make\s+me\s+laugh$', r'^funny$'],
            'motivation': [r'^motivate\s+me$', r'^inspire\s+me$', r'^encouragement$'],
        }

    def classify(self, text: str) -> Dict[str, Any]:
        """Classify user input into intent + extracted data."""
        text_clean = text.lower().strip()
        
        # 1. Rule-based matching (fast path)
        for intent, patterns in self.intents.items():
            for pattern in patterns:
                match = re.search(pattern, text_clean)
                if match:
                    data = match.group(1) if match.groups() else None
                    return {'intent': intent, 'data': data, 'confidence': 1.0, 'method': 'rule'}
        
        # 2. LLM-based classification (for complex queries)
        if self.brain and hasattr(self.brain, 'is_available') and self.brain.is_available():
            try:
                prompt = f"""Classify the user intent for: "{text}"
Return ONLY a JSON object with 'intent' and 'data'.
Possible intents: {list(self.intents.keys())} or 'chat' for general conversation.
Example: {{"intent": "open_app", "data": "chrome"}}"""
                
                response = self.brain.generate_response(prompt, 
                    system_prompt="You are an intent classifier. Output JSON only, no markdown.")
                
                json_match = re.search(r'\{[^}]+\}', response)
                if json_match:
                    result = json.loads(json_match.group())
                    result['confidence'] = 0.8
                    result['method'] = 'llm'
                    return result
            except:
                pass
                
        # 3. Default to chat
        return {'intent': 'chat', 'data': text, 'confidence': 0.5, 'method': 'default'}


# ============================================================================
# COMMAND ROUTER - Executes Actions
# ============================================================================
class CommandRouter:
    """Routes classified intents to the appropriate system action."""
    
    def __init__(self, apps_layer=None, system_layer=None, web_layer=None, app_finder=None):
        self.apps = apps_layer
        self.system = system_layer
        self.web = web_layer
        self.app_finder = app_finder
        
    def execute(self, intent: str, data: Any) -> str:
        """Execute the given intent with data."""
        
        # --- App Control ---
        if intent == 'open_app':
            return self._open_app(data)
        elif intent == 'close_app':
            return self._close_app(data)
            
        # --- Web Actions ---
        elif intent == 'search_web':
            return self._search_web(data)
        elif intent == 'play_video':
            return self._play_video(data)
        elif intent == 'open_url':
            return self._open_url(data)
            
        # --- System Control ---
        elif intent == 'set_volume':
            return self._set_volume(data)
        elif intent == 'set_brightness':
            return self._set_brightness(data)
        elif intent == 'mute':
            return self._mute()
        elif intent == 'unmute':
            return self._unmute()
        elif intent == 'lock':
            return self._lock_screen()
        elif intent == 'shutdown':
            return self._shutdown()
        elif intent == 'restart':
            return self._restart()
            
        # --- Status ---
        elif intent == 'system_status':
            return self._get_system_status()
        elif intent == 'battery_status':
            return self._get_battery_status()
        elif intent == 'time':
            return f"The current time is {datetime.now().strftime('%I:%M %p')}"
        elif intent == 'date':
            return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}"
            
        return None  # Not a command intent
    
    # --- Private Execution Methods ---
    def _open_app(self, app_name: str) -> str:
        if not app_name:
            return "Please specify an app to open."
            
        # Try AppFinder first (smart discovery)
        if self.app_finder:
            success, msg = self.app_finder.launch_app(app_name)
            if success:
                return msg
        
        # Try AppControlLayer
        if self.apps:
            success, msg = self.apps.open_app(app_name)
            return msg
            
        # Fallback to os.system
        try:
            os.system(f'start "" "{app_name}"')
            return f"Opening {app_name}..."
        except:
            return f"Failed to open {app_name}"
    
    def _close_app(self, app_name: str) -> str:
        if not app_name:
            return "Please specify an app to close."
        if self.apps:
            success, msg = self.apps.close_app(app_name)
            return msg
        try:
            os.system(f'taskkill /IM "{app_name}.exe" /F')
            return f"Closed {app_name}"
        except:
            return f"Failed to close {app_name}"
    
    def _search_web(self, query: str) -> str:
        if self.web:
            self.web.search_google(query)
        else:
            import webbrowser
            webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        return f"Searching for: {query}"
    
    def _play_video(self, query: str) -> str:
        if self.web:
            self.web.play_youtube(query)
        else:
            import webbrowser
            webbrowser.open(f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}")
        return f"Playing: {query}"
    
    def _open_url(self, url: str) -> str:
        import webbrowser
        webbrowser.open(url)
        return f"Opening: {url}"
    
    def _set_volume(self, level: str) -> str:
        try:
            level_int = int(level)
            if self.system:
                self.system.set_volume(level_int)
            return f"Volume set to {level}%"
        except:
            return "Invalid volume level"
    
    def _set_brightness(self, level: str) -> str:
        try:
            level_int = int(level)
            if self.system:
                self.system.set_brightness(level_int)
            return f"Brightness set to {level}%"
        except:
            return "Invalid brightness level"
    
    def _mute(self) -> str:
        if self.system:
            self.system.mute()
        return "System muted"
    
    def _unmute(self) -> str:
        if self.system:
            self.system.unmute()
        return "System unmuted"
    
    def _lock_screen(self) -> str:
        if self.system:
            self.system.lock_screen()
        else:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
        return "Screen locked"
    
    def _shutdown(self) -> str:
        os.system('shutdown /s /t 60')
        return "System will shutdown in 60 seconds. Run 'shutdown /a' to cancel."
    
    def _restart(self) -> str:
        os.system('shutdown /r /t 60')
        return "System will restart in 60 seconds. Run 'shutdown /a' to cancel."
    
    def _get_system_status(self) -> str:
        if self.system:
            status = self.system.get_system_status()
            cpu = status.get('cpu_percent', 'N/A')
            mem = status.get('memory', {}).get('percent', 'N/A')
            return f"CPU: {cpu}%, Memory: {mem}%"
        return "System status unavailable"
    
    def _get_battery_status(self) -> str:
        if self.system:
            status = self.system.get_battery_status()
            if status:
                pct = status.get('percent', 'N/A')
                charging = "Charging" if status.get('charging') else "Discharging"
                return f"Battery: {pct}% ({charging})"
        return "Battery status unavailable"


# ============================================================================
# CHAT RESPONDER - Conversational Responses
# ============================================================================
class ChatResponder:
    """Handles conversational responses (greetings, jokes, help, etc.)"""
    
    GREETINGS = [
        "Hello! I'm Nova, your AI assistant. How can I help?",
        "Hi there! What can I do for you today?",
        "Hey! Ready to assist. What's on your mind?",
    ]
    FAREWELLS = [
        "Goodbye! Have a great day!",
        "See you later! Take care!",
        "Bye! Feel free to come back anytime.",
    ]
    THANKS = [
        "You're welcome! Happy to help.",
        "No problem at all!",
        "My pleasure!",
    ]
    JOKES = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "A SQL query walks into a bar, walks up to two tables and asks... 'Can I join you?'",
        "Why did the Python programmer get bitten by a snake? Because he didn't handle the exception!",
    ]
    MOTIVATION = [
        "You've got this! Believe in yourself and keep pushing forward.",
        "Every expert was once a beginner. Keep learning!",
        "Success is not final, failure is not fatal. Keep going!",
    ]
    HELP_TEXT = """I can help you with:
• Open/close apps (e.g., 'open chrome', 'close notepad')
• Search the web (e.g., 'search python tutorials')
• Play YouTube videos (e.g., 'play lofi music')
• Control volume (e.g., 'volume 50', 'mute')
• System info (e.g., 'battery', 'system status', 'time')
• Answer questions (just ask!)
• Tell jokes, motivate you, and more!"""

    def respond(self, intent: str, data: Any = None) -> str:
        if intent == 'greeting':
            return random.choice(self.GREETINGS)
        elif intent == 'farewell':
            return random.choice(self.FAREWELLS)
        elif intent == 'thanks':
            return random.choice(self.THANKS)
        elif intent == 'joke':
            return random.choice(self.JOKES)
        elif intent == 'motivation':
            return random.choice(self.MOTIVATION)
        elif intent == 'help':
            return self.HELP_TEXT
        return None


# ============================================================================
# NOVA CORE ASSISTANT - The Main Engine
# ============================================================================
class NovaCoreAssistant:
    """
    The unified Nova Core Assistant.
    Combines: Intent Classification, Command Routing, Chat, and LLM.
    """
    
    def __init__(self, user_name: str = "User"):
        # Initialize brain (LLM)
        self.brain = None
        if MultiModelBrain:
            self.brain = MultiModelBrain()
        elif GroqBrain:
            self.brain = GroqBrain()
        
        # Initialize layers
        apps = AppControlLayer() if AppControlLayer else None
        system = SystemInteractionEngine() if SystemInteractionEngine else None
        web = WebControlLayer() if WebControlLayer else None
        
        # Core components
        self.classifier = IntentClassifier(self.brain)
        self.router = CommandRouter(apps, system, web, APP_FINDER)
        self.chat = ChatResponder()
        
        self.user_name = user_name
        self.plugins: Dict[str, Callable] = {}
        self._load_default_plugins()
    
    def _load_default_plugins(self):
        """Load built-in plugins."""
        self.plugins = {
            'weather': lambda q: f"Weather info for {q}: Sunny, 25°C (mock data)",
            'calculate': self._calculate,
        }
    
    def _calculate(self, expr: str) -> str:
        """Simple calculator plugin."""
        try:
            # Basic safety: only allow math expressions
            safe_expr = re.sub(r'[^0-9+\-*/().\s]', '', expr)
            result = eval(safe_expr)
            return f"Result: {result}"
        except:
            return "Could not calculate that expression."
    
    def add_plugin(self, trigger: str, handler: Callable):
        """Add a custom plugin."""
        self.plugins[trigger] = handler
    
    def process(self, user_input: str) -> str:
        """Process user input and return a response."""
        if not user_input or not user_input.strip():
            return ""
        
        text = user_input.strip()
        
        # 1. Check plugins first
        for trigger, handler in self.plugins.items():
            if trigger in text.lower():
                try:
                    return handler(text)
                except:
                    pass
        
        # 2. Classify intent
        classification = self.classifier.classify(text)
        intent = classification.get('intent')
        data = classification.get('data')
        
        # 3. Try command execution
        cmd_result = self.router.execute(intent, data)
        if cmd_result:
            return cmd_result
        
        # 4. Try chat response
        chat_result = self.chat.respond(intent, data)
        if chat_result:
            return chat_result
        
        # 5. Fallback to LLM for general questions
        if self.brain and hasattr(self.brain, 'is_available') and self.brain.is_available():
            return self.brain.chat(text)
        elif self.brain and hasattr(self.brain, 'generate_response'):
            return self.brain.generate_response(text)
        
        return "I'm not sure how to help with that. Try 'help' for available commands."


# ============================================================================
# MAIN - Standalone CLI
# ============================================================================
def main():
    """Simple CLI for standalone use."""
    print("""
    ╔═══════════════════════════════════════════════════╗
    ║         NOVA CORE ASSISTANT (Lite Mode)           ║
    ║   Text-Only  •  Hybrid NLP  •  System Control     ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    assistant = NovaCoreAssistant(user_name="Vyas")
    print(f"Nova: Hello {assistant.user_name}! I'm ready to help. Type 'help' for commands.\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print("Nova: Goodbye! Have a great day!")
                break
            
            response = assistant.process(user_input)
            print(f"Nova: {response}\n")
            
        except KeyboardInterrupt:
            print("\nNova: Goodbye!")
            break
        except Exception as e:
            print(f"Nova: Error - {e}")


if __name__ == "__main__":
    main()
