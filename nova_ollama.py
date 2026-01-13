import json
import requests
import sys

class NovaBrain:
    """
    NovaBrain - The LLM interface for Nova System AI using Ollama.
    Connects to a local Ollama instance to provide intelligence and automation capabilities.
    """
    
    def __init__(self, model="llama3", base_url="http://localhost:11434"):
        self.base_url = base_url
        self.model = model
        self.available = False
        self.check_connection()
        
    def check_connection(self):
        """Check if Ollama is running and select a valid model."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models_data = response.json().get('models', [])
                available_models = [m['name'] for m in models_data]
                
                # Check if default model exists
                if not any(self.model in m for m in available_models):
                    # Try to find a good fallback
                    preferred_order = ['llama3', 'llama3.2', 'mistral', 'gemma', 'neural-chat', 'starling-lm', 'llama2']
                    
                    found_fallback = False
                    for pref in preferred_order:
                        for avail in available_models:
                            if pref in avail:
                                self.model = avail
                                found_fallback = True
                                break
                        if found_fallback: break
                    
                    # If still nothing, just pick the first one
                    if not found_fallback and available_models:
                        self.model = available_models[0]
                        
                # print(f"✅ Connected to Ollama (Using: {self.model})")
                self.available = True
                return True
        except:
            pass
        self.available = False
        return False
        
    def generate_response(self, prompt, system_prompt=None):
        """Generate a response from the LLM."""
        if not self.available:
            return "Error: Ollama is not connected. Please make sure Ollama is running."
            
        url = f"{self.base_url}/api/generate"
        
        full_prompt = prompt
        if system_prompt:
            # Format depends on model, but standard prompt suffix works for most
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\n\nAssistant:"
            
        data = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.7
            }
        }
        
        try:
            response = requests.post(url, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            elif response.status_code == 404:
                # MODEL NOT FOUND - Auto-healing mechanism
                # print(f"⚠️ Model '{self.model}' not found. Switching to available model...")
                
                # Fetch available models
                tags = requests.get(f"{self.base_url}/api/tags", timeout=2).json()
                models = [m['name'] for m in tags.get('models', [])]
                
                if models:
                    self.model = models[0] # Pick the first one (usually the most recent pull)
                    data['model'] = self.model
                    
                    # Retry once with new model
                    retry = requests.post(url, json=data, timeout=60)
                    if retry.status_code == 200:
                        return retry.json().get('response', '').strip()
                
                return f"Error: Model {self.model} not found and no alternatives available."
            else:
                return f"Error: Ollama returned status {response.status_code}"
        except Exception as e:
            return f"Error communicating with Ollama: {str(e)}"
            
    def interpret_automation_command(self, user_command):
        """
        Interpret a natural language command into a structured automation action.
        Returns a JSON string or dict representing the action.
        """
        system_prompt = """
        You are the automation brain for Nova System AI. Your goal is to map user requests to specific automation commands.
        
        Available Commands & Parameters:
        1. Open App: {"action": "open_app", "app": "name"}
           - Example: "open chrome", "launch spotify" -> {"action": "open_app", "app": "chrome"}
           
        2. Close App: {"action": "close_app", "app": "name"}
           - Example: "kill notepad", "close calculator" -> {"action": "close_app", "app": "notepad"}
           
        3. Web Navigation: {"action": "open_url", "url": "url"}
           - Example: "go to google.com", "open youtube" -> {"action": "open_url", "url": "google.com"}
           
        4. Web Search: {"action": "search_google", "query": "search_term"}
           - Example: "search for cats", "google python tutorials" -> {"action": "search_google", "query": "cats"}
           
        5. YouTube Play: {"action": "play_youtube", "query": "video_name"}
           - Example: "play despacito", "play tech news" -> {"action": "play_youtube", "query": "despacito"}
           
        6. Volume Control: {"action": "set_volume", "level": number}
           - Example: "volume 50", "turn it up" -> {"action": "set_volume", "level": 75}
           
        7. Mute: {"action": "mute"}
        8. Unmute: {"action": "unmute"}
        
        9. Brightness: {"action": "set_brightness", "level": number}
           - Example: "brightness 80", "dim screen" -> {"action": "set_brightness", "level": 30}
           
        10. System: {"action": "lock"} (Lock screen), {"action": "sleep"} (Sleep), {"action": "shutdown"}, {"action": "restart"}
        
        11. Type Text: {"action": "type", "text": "content"}
            - Example: "type hello world" -> {"action": "type", "text": "hello world"}
            
        12. Chat: {"action": "chat", "response": "AI response"}
            - Use this ONLY if the user's request is purely conversational (e.g. "hi", "how are you", "tell me a joke").
            - NEVER use this to say "I can't do that". Instead, finding the closest matching automation action.
            
        MULTI-STEP COMMANDS:
        If the user asks for multiple things (e.g., "open chrome and search for cats"), you can return a LIST of action objects.
        Example: [{"action": "open_app", "app": "chrome"}, {"action": "search_google", "query": "cats"}]
        
        CRITICAL RULES:
        1. IF the user asks to "take notes" or "write down", map this to OPENING A TEXT EDITOR.
           - "take notes on ml" -> [{"action": "open_app", "app": "notepad"}, {"action": "type", "text": "Notes on ML: ..."}]
           - "open chrome and take notes" -> [{"action": "open_app", "app": "chrome"}, {"action": "open_app", "app": "notepad"}]
           
        2. IF the user asks to "search" or "learn about", map this to A GOOGLE SEARCH.
           - "learn about stars" -> {"action": "search_google", "query": "stars"}
           
        3. DO NOT output conversational fillers like "Here is the information". JUST OUTPUT THE JSON ACTION.
        4. Do NOT say "I cannot interact using apps". You ARE the interface. Output the JSON command to make it happen.
            
        OUTPUT FORMAT:
        Return ONLY valid JSON. START and END with valid JSON (object or list). Do not include markdown formatting or explanations.
        """
        
        response = self.generate_response(user_command, system_prompt)
        
        # Clean up response to ensure it's valid JSON
        clean_response = response.strip()
        if clean_response.startswith('```json'):
            clean_response = clean_response[7:]
        if clean_response.endswith('```'):
            clean_response = clean_response[:-3]
        
        try:
            return json.loads(clean_response)
        except:
            # If JSON parsing fails, treat it as a chat response
            return {"action": "chat", "response": response}

if __name__ == "__main__":
    brain = NovaBrain()
    if brain.available:
        print("Brain is active.")
        while True:
            cmd = input("You: ")
            if cmd.lower() == 'exit': break
            print(brain.interpret_automation_command(cmd))
    else:
        print("Ollama not found.")
