#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA LAYERED ASSISTANT
=======================
A modular, conversational AI assistant with separate layers for:
1. Conversation Layer → Natural chat, always responsive
2. Learning Layer → Silently logs user habits, preferences, context
3. Coding Layer → Generates plugins on-demand (trigger-based)

Architecture:
- Modular prompts (System, Developer, Memory)
- Plugin-based extensibility
- Self-coding only when explicitly requested or patterns detected
"""

import os
import sys
import json
import re
import importlib.util
from datetime import datetime
from typing import Optional, Dict, List, Any, Callable
from pathlib import Path

# Project root
SCRIPT_DIR = Path(__file__).parent.resolve()
PLUGINS_DIR = SCRIPT_DIR / "plugins"
MEMORY_FILE = SCRIPT_DIR / "user_memory.json"
HABITS_FILE = SCRIPT_DIR / "user_habits.json"

# Ensure plugins directory exists
PLUGINS_DIR.mkdir(exist_ok=True)

# Import the multi-model brain
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from nova_system.multi_model_brain import MultiModelBrain
except ImportError:
    MultiModelBrain = None


# ============================================================================
# MODULAR PROMPTS
# ============================================================================
class NovaPrompts:
    """Modular prompt system for Nova."""
    
    SYSTEM_PROMPT = """You are Nova, a friendly and helpful AI assistant.
You are conversational, warm, and efficient. Always respond naturally.
Keep responses concise unless the user asks for detail.
Never say you can't help - if you don't have a feature, offer to create one."""

    DEVELOPER_PROMPT = """You are a Python developer creating plugins for Nova.
When asked to create a new feature, generate a complete Python plugin with:
1. A clear docstring explaining what it does
2. A main function that can be called with optional parameters
3. Error handling for edge cases
4. Return a string result that can be shown to the user

Plugin Template:
```python
\"\"\"
Plugin: [Name]
Description: [What it does]
Author: Nova Auto-Generated
\"\"\"

def run(params: dict = None) -> str:
    \"\"\"Main entry point for the plugin.\"\"\"
    try:
        # Implementation here
        return "Result message"
    except Exception as e:
        return f"Error: {e}"
```"""

    MEMORY_PROMPT = """You remember user preferences and adapt your tone.
Known preferences:
{preferences}

Recent interactions:
{recent_history}

Adapt your responses based on this context."""

    INTENT_CLASSIFIER_PROMPT = """Classify the user's intent from this message: "{message}"

Possible intents:
- "chat": General conversation, greeting, or question
- "execute": User wants to run an existing command/plugin
- "create": User wants a new feature or plugin
- "learn": User is sharing a preference or personal info
- "system": User wants to control the laptop (open apps, volume, settings, etc.)

Respond with ONLY a JSON object:
{{"intent": "...", "action": "...", "params": {{}}}}

Examples:
- "Hey, how are you?" → {{"intent": "chat", "action": null, "params": {{}}}}
- "Open Chrome" → {{"intent": "system", "action": "open", "params": {{"app": "chrome"}}}}
- "Turn up the volume" → {{"intent": "system", "action": "volume", "params": {{"direction": "up"}}}}
- "Create a plugin to monitor CPU" → {{"intent": "create", "action": "monitor_cpu", "params": {{}}}}
"""


# ============================================================================
# LEARNING LAYER
# ============================================================================
class LearningLayer:
    """Silently learns user habits, preferences, and context."""
    
    def __init__(self):
        self.preferences = self._load_json(MEMORY_FILE, {})
        self.habits = self._load_json(HABITS_FILE, {"commands": {}, "times": []})
        self.session_history: List[Dict] = []
    
    def _load_json(self, path: Path, default: dict) -> dict:
        try:
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return default
    
    def _save_json(self, path: Path, data: dict):
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except:
            pass
    
    def log_interaction(self, user_input: str, response: str, intent: str):
        """Log an interaction for learning."""
        entry = {
            "time": datetime.now().isoformat(),
            "input": user_input,
            "response": response[:100],
            "intent": intent
        }
        self.session_history.append(entry)
        
        # Track command usage patterns
        if intent == "execute":
            action = user_input.lower().split()[0] if user_input else ""
            self.habits["commands"][action] = self.habits["commands"].get(action, 0) + 1
        
        # Log time patterns
        hour = datetime.now().hour
        self.habits["times"].append(hour)
        if len(self.habits["times"]) > 100:
            self.habits["times"] = self.habits["times"][-50:]
        
        self._save_json(HABITS_FILE, self.habits)
    
    def learn_preference(self, key: str, value: str):
        """Store a user preference."""
        self.preferences[key] = value
        self._save_json(MEMORY_FILE, self.preferences)
    
    def get_preference(self, key: str, default: str = None) -> str:
        return self.preferences.get(key, default)
    
    def get_context_summary(self) -> str:
        """Get a summary of learned context."""
        prefs = ", ".join(f"{k}={v}" for k, v in self.preferences.items()) or "None yet"
        recent = self.session_history[-5:] if self.session_history else []
        history = "\n".join(f"- {h['input'][:50]}" for h in recent) or "None yet"
        return f"Preferences: {prefs}\nRecent: {history}"
    
    def detect_patterns(self) -> List[str]:
        """Detect repeated patterns that might warrant new plugins."""
        suggestions = []
        for cmd, count in self.habits["commands"].items():
            if count >= 3 and cmd not in ["hello", "hi", "hey", "thanks"]:
                suggestions.append(f"User frequently asks about '{cmd}' - consider a plugin")
        return suggestions


# ============================================================================
# CODING LAYER
# ============================================================================
class CodingLayer:
    """Generates and manages plugins dynamically."""
    
    def __init__(self, brain):
        self.brain = brain
        self.loaded_plugins: Dict[str, Callable] = {}
        self._load_existing_plugins()
    
    def _load_existing_plugins(self):
        """Load all existing plugins from the plugins directory."""
        if not PLUGINS_DIR.exists():
            return
        
        for plugin_file in PLUGINS_DIR.glob("*.py"):
            if plugin_file.name.startswith("_"):
                continue
            try:
                self._load_plugin(plugin_file)
            except Exception as e:
                print(f"Warning: Failed to load {plugin_file.name}: {e}")
    
    def _load_plugin(self, path: Path):
        """Load a single plugin."""
        name = path.stem
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'run'):
            self.loaded_plugins[name] = module.run
            return True
        return False
    
    def has_plugin(self, name: str) -> bool:
        """Check if a plugin exists."""
        # Normalize name
        normalized = name.lower().replace(" ", "_").replace("-", "_")
        return normalized in self.loaded_plugins
    
    def run_plugin(self, name: str, params: dict = None) -> str:
        """Execute a plugin."""
        normalized = name.lower().replace(" ", "_").replace("-", "_")
        
        if normalized not in self.loaded_plugins:
            return None  # Plugin doesn't exist
        
        try:
            return self.loaded_plugins[normalized](params or {})
        except Exception as e:
            return f"Plugin error: {e}"
    
    def list_plugins(self) -> List[str]:
        """List all available plugins."""
        return list(self.loaded_plugins.keys())
    
    def generate_plugin(self, name: str, description: str) -> tuple[bool, str]:
        """Generate a new plugin using the AI brain."""
        if not self.brain or not self.brain.is_available():
            return False, "AI brain not available for code generation"
        
        prompt = f"""Create a Python plugin for Nova assistant.

Plugin Name: {name}
Description: {description}

Requirements:
1. Must have a `run(params: dict = None) -> str` function
2. Include a docstring at the top
3. Handle errors gracefully
4. Return a user-friendly string result
5. Use only standard library or common packages (os, subprocess, psutil)

Generate ONLY the Python code, no markdown:"""

        try:
            code = self.brain.generate_response(prompt, NovaPrompts.DEVELOPER_PROMPT)
            
            # Clean up the code
            code = code.strip()
            if code.startswith("```python"):
                code = code[9:]
            if code.startswith("```"):
                code = code[3:]
            if code.endswith("```"):
                code = code[:-3]
            code = code.strip()
            
            # Save the plugin
            plugin_path = PLUGINS_DIR / f"{name.lower().replace(' ', '_')}.py"
            with open(plugin_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Load it
            self._load_plugin(plugin_path)
            
            return True, f"Plugin '{name}' created and loaded successfully!"
        
        except Exception as e:
            return False, f"Failed to generate plugin: {e}"


# ============================================================================
# CONVERSATION LAYER
# ============================================================================
class ConversationLayer:
    """Handles natural conversation with the user."""
    
    def __init__(self, brain, learning: LearningLayer):
        self.brain = brain
        self.learning = learning
        self.coding_layer_ref = None # Will be set by NovaLayeredAssistant
    
    def classify_intent(self, message: str) -> Dict:
        """Classify the user's intent."""
        # Quick rule-based classification for common patterns
        msg_lower = message.lower().strip()
        
        # Greetings
        if msg_lower in ["hi", "hello", "hey", "good morning", "good evening"]:
            return {"intent": "chat", "action": None, "params": {}}
        
        # Thanks
        if any(w in msg_lower for w in ["thank", "thanks", "cheers"]):
            return {"intent": "chat", "action": None, "params": {}}
        
        # Exit
        if msg_lower in ["exit", "quit", "bye", "goodbye"]:
            return {"intent": "exit", "action": None, "params": {}}
        
        # Create requests
        if any(w in msg_lower for w in ["create a", "make a", "build a", "generate a", "add a feature", "new plugin"]):
            return {"intent": "create", "action": msg_lower, "params": {}}
            
        # System Control (Open/Launch)
        if any(msg_lower.startswith(w + " ") for w in ["open", "launch", "start", "run"]):
            app = msg_lower.split(" ", 1)[1].strip()
            return {"intent": "system", "action": "open", "params": {"app": app}}
        
        # CHECK IF IT MATCHES AN EXISTING PLUGIN
        # This is high priority for the layered assistant
        plugin_name = msg_lower.replace(" ", "_")
        # Check direct match or first two words
        if self.learning and hasattr(self, 'coding'): # This is inside ConversationLayer, need coding reference
             pass # Will handle in a better way below

        # Use AI for more complex classification
        if self.brain and self.brain.is_available():
            try:
                # Add list of available plugins to the prompt to help the LLM
                available_plugins = ""
                if hasattr(self, 'coding_layer_ref') and self.coding_layer_ref:
                    available_plugins = f"\nAvailable plugins: {', '.join(self.coding_layer_ref.list_plugins())}"

                prompt = NovaPrompts.INTENT_CLASSIFIER_PROMPT.format(message=message) + available_plugins
                response = self.brain.generate_response(prompt)
                
                # Extract JSON
                json_match = re.search(r'\{[^}]+\}', response)
                if json_match:
                    return json.loads(json_match.group())
            except:
                pass
        
        # Final fallback check for common plugin names even without AI
        if hasattr(self, 'coding_layer_ref') and self.coding_layer_ref:
            for p_name in self.coding_layer_ref.list_plugins():
                # Check if plugin name is in the message
                if p_name.replace("_", " ") in msg_lower:
                    return {"intent": "execute", "action": p_name, "params": {}}

        # Default to chat
        return {"intent": "chat", "action": None, "params": {}}
    
    def generate_response(self, message: str, context: str = "") -> str:
        """Generate a conversational response."""
        if not self.brain or not self.brain.is_available():
            return self._fallback_response(message)
        
        # Build context-aware prompt
        memory_context = self.learning.get_context_summary()
        full_prompt = f"{context}\n\nUser Context:\n{memory_context}\n\nUser: {message}"
        
        try:
            return self.brain.generate_response(full_prompt, NovaPrompts.SYSTEM_PROMPT)
        except:
            return self._fallback_response(message)
    
    def _fallback_response(self, message: str) -> str:
        """Fallback responses when AI is unavailable."""
        msg_lower = message.lower()
        
        if any(w in msg_lower for w in ["hi", "hello", "hey"]):
            return "Hello! How can I help you today?"
        if "time" in msg_lower:
            return f"The current time is {datetime.now().strftime('%I:%M %p')}"
        if "date" in msg_lower:
            return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}"
        
        return "I'm here to help! What would you like to do?"


# ============================================================================
# NOVA LAYERED ASSISTANT - Main Class
# ============================================================================
class NovaLayeredAssistant:
    """
    The main Nova Layered Assistant.
    Combines Conversation, Learning, and Coding layers.
    """
    
    def __init__(self, user_name: str = "User"):
        self.user_name = user_name
        
        # Initialize brain
        self.brain = MultiModelBrain() if MultiModelBrain else None
        
        # Initialize layers
        self.learning = LearningLayer()
        self.coding = CodingLayer(self.brain)
        self.conversation = ConversationLayer(self.brain, self.learning)
        self.conversation.coding_layer_ref = self.coding # Link them
        
        # Pending actions
        self.pending_create: Optional[Dict] = None
    
    def process(self, user_input: str) -> str:
        """Process user input and return a response."""
        if not user_input or not user_input.strip():
            return ""
        
        message = user_input.strip()
        
        # Handle pending creation confirmation
        if self.pending_create:
            return self._handle_pending_create(message)
        
        # Classify intent
        classification = self.conversation.classify_intent(message)
        intent = classification.get("intent", "chat")
        action = classification.get("action")
        params = classification.get("params", {})
        
        # Route to appropriate handler
        if intent == "exit":
            response = f"Goodbye, {self.user_name}! See you next time."
        elif intent == "execute":
            response = self._handle_execute(message, action, params)
        elif intent == "create":
            response = self._handle_create_request(message, action)
        elif intent == "system":
            response = self._handle_system(action, params)
        elif intent == "learn":
            response = self._handle_learn(params)
        else:
            response = self.conversation.generate_response(message)
        
        # Log interaction for learning
        self.learning.log_interaction(message, response, intent)
        
        return response
    
    def _handle_execute(self, message: str, action: str, params: dict) -> str:
        """Handle execution of a command or plugin."""
        # Try to find and run a matching plugin
        plugin_names = [
            action,
            action.replace(" ", "_"),
            message.lower().replace(" ", "_"),
            "_".join(message.lower().split()[:2])
        ]
        
        for name in plugin_names:
            if self.coding.has_plugin(name):
                result = self.coding.run_plugin(name, params)
                if result:
                    return f"[OK] {result}"
        
        # Plugin doesn't exist - offer to create it
        self.pending_create = {"name": action or message, "description": message}
        return f"I don't have a plugin for that yet. Would you like me to create one for '{action or message}'? (yes/no)"
    
    def _handle_create_request(self, message: str, action: str) -> str:
        """Handle explicit request to create a new feature."""
        # Extract what they want
        match = re.search(r'(?:create|make|build|generate)\s+(?:a\s+)?(?:plugin\s+)?(?:for\s+|to\s+)?(.+)', message.lower())
        name = match.group(1) if match else action
        
        self.pending_create = {"name": name, "description": message}
        return f"I can create a plugin for '{name}'. Should I proceed? (yes/no)"
    
    def _handle_pending_create(self, response: str) -> str:
        """Handle confirmation for pending plugin creation."""
        response_lower = response.lower().strip()
        
        if response_lower in ["yes", "y", "yeah", "sure", "ok", "okay", "go ahead"]:
            name = self.pending_create["name"]
            desc = self.pending_create["description"]
            self.pending_create = None
            
            success, message = self.coding.generate_plugin(name, desc)
            if success:
                return f"[OK] {message}\n\nYou can now use this feature. Just ask!"
            else:
                return f"Sorry, I couldn't create the plugin: {message}"
        else:
            self.pending_create = None
            return "No problem! Let me know if you need anything else."
    
    def _handle_learn(self, params: dict) -> str:
        """Handle learning a new preference."""
        key = params.get("key")
        value = params.get("value")
        
        if key and value:
            self.learning.learn_preference(key, value)
            return f"Got it! I'll remember that you prefer {key}: {value}"
        
        return "I've noted that. Thanks for letting me know!"

    def _handle_system(self, action: str, params: dict) -> str:
        """Handle system control commands."""
        import subprocess
        
        if action == "open":
            app = params.get("app", "")
            if app:
                try:
                    # Try common windows path or just start
                    os.system(f'start "" "{app}"')
                    return f"I've sent the command to open {app}."
                except Exception as e:
                    return f"Failed to open {app}: {e}"
                    
        elif action == "volume":
            direction = params.get("direction", "")
            if direction == "up":
                os.system("nircmd.exe changesysvolume 5000") # If nircmd available
                return "Increasing volume..."
            elif direction == "down":
                os.system("nircmd.exe changesysvolume -5000")
                return "Decreasing volume..."
                
        return "Command received, but I'm still learning how to control that part of the laptop."


# ============================================================================
# MAIN - Interactive CLI
# ============================================================================
def main():
    """Interactive CLI for Nova Layered Assistant."""
    print("""
    ===============================================================
                   NOVA LAYERED ASSISTANT
           Conversation - Learning - Self-Coding
    ===============================================================
    """)
    
    assistant = NovaLayeredAssistant(user_name="Vyas")
    
    # Show available plugins
    plugins = assistant.coding.list_plugins()
    if plugins:
        print(f"  [Plugins] Loaded: {', '.join(plugins)}")
    else:
        print("  [Plugins] None loaded. I can create them on request!")
    
    print(f"\n  Nova: Hello {assistant.user_name}! I'm ready to help.\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            response = assistant.process(user_input)
            print(f"Nova: {response}\n")
            
            if "Goodbye" in response:
                break
                
        except KeyboardInterrupt:
            print("\nNova: Goodbye!")
            break
        except Exception as e:
            print(f"Nova: Sorry, an error occurred: {e}\n")


if __name__ == "__main__":
    main()
