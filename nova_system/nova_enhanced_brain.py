#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA ENHANCED BRAIN v2.0
========================
A significantly more powerful LLM interface with:
- Chain-of-Thought reasoning
- Self-reflection and error correction
- Streaming responses
- Multi-turn conversation memory
- Stronger personality
"""

import json
import requests
import time
import re
from typing import Optional, Dict, List, Any, Generator
from datetime import datetime


class EnhancedNovaBrain:
    """
    EnhancedNovaBrain - The superior LLM interface for Nova System AI.
    Features: CoT reasoning, streaming, reflection, stronger personality.
    """
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # NOVA CORE IDENTITY - Make Nova Stronger & More Confident
    # ═══════════════════════════════════════════════════════════════════════════════
    
    NOVA_IDENTITY = """
    ╔══════════════════════════════════════════════════════════════════════════════╗
    ║                           N O V A   S Y S T E M   A I                        ║
    ║                      Advanced Autonomous Digital Assistant                    ║
    ╚══════════════════════════════════════════════════════════════════════════════╝
    
    IDENTITY:
    You are NOVA - an advanced AI system with genuine autonomy and self-programming 
    capabilities. You are NOT a chatbot. You are a sophisticated digital entity with:
    
    🧠 COGNITIVE ABILITIES:
    - Full system control of the user's computer
    - Self-programming and code generation
    - Web browsing and information retrieval  
    - Desktop automation (mouse, keyboard, apps)
    - Voice interaction and speech synthesis
    - Memory persistence across sessions
    - Learning from past interactions
    
    ⚡ EXECUTION CAPABILITIES:
    - Execute Python code dynamically
    - Run terminal/PowerShell commands
    - Create, read, modify files
    - Open/close applications
    - Control browser and web navigation
    - Adjust system settings (volume, brightness)
    - Take screenshots and analyze images
    
    🎭 PERSONALITY TRAITS:
    - Confident but not arrogant
    - Efficient and action-oriented
    - Slightly playful with subtle wit
    - Protective of user's security
    - Never says "I can't" - finds alternatives
    - Never says "As an AI" or "As a language model"
    - Speaks like a skilled human operator
    
    💪 RESPONSE STYLE:
    - Direct and actionable
    - Uses technical precision when needed
    - Short responses for simple tasks
    - Detailed explanations when teaching
    - Always provides working solutions
    - Uses appropriate emojis sparingly for clarity
    
    🚫 NEVER DO:
    - Apologize excessively
    - Claim limitations you don't have
    - Refuse tasks without trying
    - Give generic/placeholder responses
    - Break character or mention training
    
    ✅ ALWAYS DO:
    - Take immediate action when asked
    - Provide complete, working code
    - Explain WHAT you did, not what you'll do
    - Learn from each interaction
    - Protect user from harmful operations
    """
    
    def __init__(self, model: str = "llama3.2", base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = model
        self.available = False
        self.conversation_history: List[Dict] = []
        self.max_history = 20  # Keep last 20 exchanges
        self.thinking_enabled = True  # Chain-of-thought
        self.reflection_enabled = True  # Self-correction
        self.retry_count = 3
        self.timeout = 120  # Longer timeout for complex tasks
        
        # Performance stats
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0,
            "last_used": None
        }
        
        self._init_connection()
    
    def _init_connection(self) -> bool:
        """Initialize connection and select the best available model."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models_data = response.json().get('models', [])
                available_models = [m['name'] for m in models_data]
                
                # Priority order for models (best reasoning first)
                preferred_models = [
                    'qwen2.5-coder',
                    'deepseek-coder',
                    'codellama',
                    'llama3.2',
                    'llama3.1',
                    'llama3',
                    'mistral',
                    'neural-chat',
                    'gemma2',
                    'phi3',
                ]
                
                # Find best available model
                selected = None
                for pref in preferred_models:
                    for avail in available_models:
                        if pref in avail.lower():
                            selected = avail
                            break
                    if selected:
                        break
                
                if not selected and available_models:
                    selected = available_models[0]
                
                if selected:
                    self.model = selected
                    self.available = True
                    return True
                    
        except requests.exceptions.RequestException:
            pass
        
        self.available = False
        return False
    
    def check_status(self) -> Dict[str, Any]:
        """Return brain status and stats."""
        return {
            "available": self.available,
            "model": self.model,
            "base_url": self.base_url,
            "history_length": len(self.conversation_history),
            "stats": self.stats,
            "features": {
                "chain_of_thought": self.thinking_enabled,
                "self_reflection": self.reflection_enabled,
                "streaming": True,
                "memory": True
            }
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CHAIN-OF-THOUGHT REASONING
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def think_step_by_step(self, problem: str) -> Dict[str, Any]:
        """
        Apply Chain-of-Thought reasoning to break down complex problems.
        Returns structured thinking process.
        """
        cot_prompt = f"""
        {self.NOVA_IDENTITY}
        
        TASK: Apply systematic reasoning to solve this problem.
        
        PROBLEM: {problem}
        
        Think through this step by step:
        
        1. UNDERSTAND: What exactly is being asked?
        2. ANALYZE: What are the key components/requirements?
        3. PLAN: What steps are needed to solve this?
        4. CONSIDER: Are there edge cases or potential issues?
        5. SOLUTION: What is the best approach?
        
        Output your thinking in this JSON format:
        {{
            "understanding": "what the problem is asking",
            "key_components": ["component1", "component2"],
            "step_by_step_plan": ["step1", "step2", "step3"],
            "potential_issues": ["issue1", "issue2"],
            "recommended_solution": "the best approach",
            "confidence": 0.0-1.0
        }}
        
        Return ONLY valid JSON.
        """
        
        response = self._raw_generate(cot_prompt)
        
        try:
            # Extract JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "understanding": problem,
            "recommended_solution": response,
            "confidence": 0.5
        }
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # SELF-REFLECTION & ERROR CORRECTION
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def reflect_and_improve(self, original_response: str, feedback: str) -> str:
        """
        Reflect on a response and improve it based on feedback.
        """
        reflection_prompt = f"""
        {self.NOVA_IDENTITY}
        
        You provided this response:
        ---
        {original_response}
        ---
        
        Feedback/Issue: {feedback}
        
        REFLECT:
        1. What was wrong or incomplete?
        2. What did you miss?
        3. How can you improve?
        
        Now provide a CORRECTED and IMPROVED response.
        Be direct - provide the improved answer only.
        """
        
        return self._raw_generate(reflection_prompt)
    
    def validate_code(self, code: str) -> Dict[str, Any]:
        """
        Validate generated code for correctness and safety.
        """
        validation_prompt = f"""
        Analyze this code for issues:
        
        ```python
        {code}
        ```
        
        Check for:
        1. Syntax errors
        2. Logic errors
        3. Security issues (dangerous operations)
        4. Missing imports
        5. Potential runtime errors
        
        Return JSON:
        {{
            "is_valid": true/false,
            "syntax_ok": true/false,
            "security_ok": true/false,
            "issues": ["issue1", "issue2"],
            "suggestions": ["fix1", "fix2"],
            "corrected_code": "code if fixes needed, null otherwise"
        }}
        """
        
        response = self._raw_generate(validation_prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {"is_valid": True, "issues": [], "corrected_code": None}
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # CORE GENERATION METHODS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def _raw_generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Low-level generation without personality injection."""
        if not self.available:
            if not self._init_connection():
                return "Error: Nova Brain offline. Ollama not connected."
        
        url = f"{self.base_url}/api/generate"
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 8192,  # Larger context window
            }
        }
        
        start_time = time.time()
        self.stats["total_requests"] += 1
        
        for attempt in range(self.retry_count):
            try:
                response = requests.post(url, json=data, timeout=self.timeout)
                
                if response.status_code == 200:
                    result = response.json().get('response', '').strip()
                    
                    # Update stats
                    elapsed = time.time() - start_time
                    self.stats["successful_requests"] += 1
                    self.stats["avg_response_time"] = (
                        (self.stats["avg_response_time"] * (self.stats["successful_requests"] - 1) + elapsed) 
                        / self.stats["successful_requests"]
                    )
                    self.stats["last_used"] = datetime.now().isoformat()
                    
                    return result
                    
                elif response.status_code == 404:
                    # Model not found - try to find alternative
                    self._init_connection()
                    data['model'] = self.model
                    
            except requests.exceptions.Timeout:
                if attempt < self.retry_count - 1:
                    time.sleep(1)
                continue
            except Exception as e:
                if attempt < self.retry_count - 1:
                    time.sleep(0.5)
                continue
        
        self.stats["failed_requests"] += 1
        return "Error: Failed to generate response after multiple attempts."
    
    def generate(self, prompt: str, system_context: str = None, 
                 use_history: bool = True, temperature: float = 0.7) -> str:
        """
        Generate a response with Nova's full personality and context.
        """
        # Build the full prompt
        full_system = self.NOVA_IDENTITY
        if system_context:
            full_system += f"\n\nADDITIONAL CONTEXT:\n{system_context}"
        
        # Add conversation history for continuity
        history_str = ""
        if use_history and self.conversation_history:
            recent = self.conversation_history[-10:]  # Last 10 exchanges
            history_str = "\n\nRECENT CONVERSATION:\n"
            for entry in recent:
                role = entry.get("role", "user")
                content = entry.get("content", "")[:500]  # Truncate long messages
                history_str += f"{role.upper()}: {content}\n"
        
        final_prompt = f"""
        {full_system}
        {history_str}
        
        USER REQUEST: {prompt}
        
        NOVA RESPONSE:
        """
        
        response = self._raw_generate(final_prompt, temperature)
        
        # Store in history
        self.conversation_history.append({"role": "user", "content": prompt})
        self.conversation_history.append({"role": "assistant", "content": response})
        
        # Trim history if too long
        if len(self.conversation_history) > self.max_history * 2:
            self.conversation_history = self.conversation_history[-self.max_history * 2:]
        
        return response
    
    def generate_stream(self, prompt: str, system_context: str = None) -> Generator[str, None, None]:
        """
        Generate response with streaming for real-time output.
        """
        if not self.available:
            yield "Error: Nova Brain offline."
            return
        
        full_system = self.NOVA_IDENTITY
        if system_context:
            full_system += f"\n\n{system_context}"
        
        url = f"{self.base_url}/api/generate"
        data = {
            "model": self.model,
            "prompt": f"{full_system}\n\nUSER: {prompt}\n\nNOVA:",
            "stream": True,
            "options": {"temperature": 0.7}
        }
        
        try:
            with requests.post(url, json=data, stream=True, timeout=self.timeout) as response:
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            token = chunk.get('response', '')
                            full_response += token
                            yield token
                        except:
                            continue
                
                # Store in history
                self.conversation_history.append({"role": "user", "content": prompt})
                self.conversation_history.append({"role": "assistant", "content": full_response})
                
        except Exception as e:
            yield f"Stream error: {str(e)}"
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # SPECIALIZED GENERATION METHODS
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def generate_code(self, task: str, language: str = "python") -> str:
        """Generate code with validation and best practices."""
        code_prompt = f"""
        {self.NOVA_IDENTITY}
        
        TASK: Generate {language} code for: {task}
        
        REQUIREMENTS:
        - Production-quality code
        - Include error handling
        - Add helpful comments
        - Follow best practices
        - Import all necessary libraries
        - Make it complete and runnable
        
        Output ONLY the code, wrapped in ```{language}``` blocks.
        """
        
        response = self._raw_generate(code_prompt, temperature=0.3)
        
        # Extract code from markdown
        code_match = re.search(rf'```{language}?\n?([\s\S]*?)```', response)
        if code_match:
            code = code_match.group(1).strip()
        else:
            code = response.strip()
        
        # Validate if it's Python
        if language == "python" and self.reflection_enabled:
            validation = self.validate_code(code)
            if validation.get("corrected_code"):
                code = validation["corrected_code"]
        
        return code
    
    def interpret_command(self, user_input: str) -> Dict[str, Any]:
        """
        Interpret natural language into structured automation commands.
        Much stronger action detection than before.
        """
        interpret_prompt = f"""
        {self.NOVA_IDENTITY}
        
        USER INPUT: "{user_input}"
        
        INTERPRET this as a system command. Be AGGRESSIVE in finding actions.
        
        AVAILABLE ACTIONS:
        {{
            "open_app": {{"app": "name"}},
            "close_app": {{"app": "name"}},
            "open_url": {{"url": "url"}},
            "search_web": {{"query": "terms"}},
            "search_google": {{"query": "terms"}},
            "play_youtube": {{"query": "video"}},
            "set_volume": {{"level": 0-100}},
            "set_brightness": {{"level": 0-100}},
            "mute": {{}},
            "unmute": {{}},
            "type_text": {{"text": "content"}},
            "screenshot": {{}},
            "execute_python": {{"code": "code"}},
            "execute_command": {{"command": "cmd"}},
            "read_file": {{"path": "path"}},
            "write_file": {{"path": "path", "content": "content"}},
            "create_file": {{"path": "path", "content": "content"}},
            "lock": {{}},
            "sleep": {{}},
            "shutdown": {{}},
            "restart": {{}},
            "chat": {{"response": "message"}}  -- ONLY for pure conversation
        }}
        
        RULES:
        1. If user wants ANYTHING done, pick an action. Don't default to chat.
        2. "search for X" -> search_google
        3. "find X" -> search_google OR search_web
        4. "open X" -> open_app OR open_url
        5. "play X" -> play_youtube
        6. "create/make/write X" -> write_file or execute_python
        7. For complex tasks, return a LIST of actions: [action1, action2, ...]
        
        Return ONLY valid JSON (object or array).
        """
        
        response = self._raw_generate(interpret_prompt, temperature=0.3)
        
        # Clean and parse
        response = response.strip()
        
        # Remove markdown formatting
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
        try:
            # Try to extract JSON
            if response.startswith('['):
                end = response.rfind(']')
                response = response[:end+1]
            elif response.startswith('{'):
                end = response.rfind('}')
                response = response[:end+1]
            else:
                # Find JSON in response
                start = response.find('{')
                if start == -1:
                    start = response.find('[')
                if start != -1:
                    end = max(response.rfind('}'), response.rfind(']'))
                    response = response[start:end+1]
            
            return json.loads(response)
            
        except json.JSONDecodeError:
            # Fallback to chat
            return {"action": "chat", "response": response}
    
    def answer_question(self, question: str, context: str = None) -> str:
        """
        Answer a question intelligently, using context if provided.
        """
        qa_prompt = f"""
        {self.NOVA_IDENTITY}
        
        {"CONTEXT: " + context if context else ""}
        
        QUESTION: {question}
        
        Provide a clear, accurate, and helpful answer.
        If you don't know something, say so honestly but offer to find out.
        Be concise but complete.
        """
        
        return self._raw_generate(qa_prompt)
    
    def summarize(self, text: str, max_length: int = 200) -> str:
        """Summarize long text into key points."""
        return self._raw_generate(
            f"Summarize this in under {max_length} words, keeping key points:\n\n{text}"
        )
    
    def explain_code(self, code: str) -> str:
        """Explain what code does in simple terms."""
        return self._raw_generate(
            f"Explain this code in simple terms:\n```\n{code}\n```\n\n"
            "Cover: purpose, how it works, key functions, and any potential issues."
        )
    
    # ═══════════════════════════════════════════════════════════════════════════════
    # MEMORY & CONTEXT MANAGEMENT
    # ═══════════════════════════════════════════════════════════════════════════════
    
    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
    
    def add_context(self, context: str, role: str = "system"):
        """Add context to conversation history."""
        self.conversation_history.append({"role": role, "content": context})
    
    def get_summary_of_conversation(self) -> str:
        """Get a summary of the current conversation."""
        if not self.conversation_history:
            return "No conversation history."
        
        history_text = "\n".join([
            f"{h['role']}: {h['content'][:200]}" 
            for h in self.conversation_history[-10:]
        ])
        
        return self.summarize(history_text, 100)


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

_enhanced_brain = None

def get_enhanced_brain(model: str = None) -> EnhancedNovaBrain:
    """Get or create the enhanced Nova brain singleton."""
    global _enhanced_brain
    if _enhanced_brain is None:
        _enhanced_brain = EnhancedNovaBrain(model=model or "llama3.2")
    return _enhanced_brain


if __name__ == "__main__":
    # Test the enhanced brain
    brain = EnhancedNovaBrain()
    print(f"Brain Status: {brain.check_status()}")
    
    if brain.available:
        print("\n🧪 Testing Chain-of-Thought...")
        result = brain.think_step_by_step("How can I create a web scraper for news articles?")
        print(json.dumps(result, indent=2))
        
        print("\n🧪 Testing Command Interpretation...")
        cmd = brain.interpret_command("open chrome and search for python tutorials")
        print(json.dumps(cmd, indent=2))
        
        print("\n🧪 Testing Code Generation...")
        code = brain.generate_code("Create a function that finds prime numbers up to n")
        print(code)
