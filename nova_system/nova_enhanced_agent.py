#!/usr/bin/env python3
"""
NOVA ENHANCED AGENT v2.0
========================
A significantly stronger autonomous agent with:
- Chain-of-Thought reasoning
- Self-reflection and error correction
- Persistent memory across sessions
- More tools and capabilities
- Better planning for complex tasks
"""
import os, sys, json, time, subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import Nova components
try:
    from nova_system.nova_enhanced_brain import EnhancedNovaBrain, get_enhanced_brain
    ENHANCED_BRAIN = True
except:
    ENHANCED_BRAIN = False
    
try:
    from nova_system.nova_tools import get_tool_registry, ToolResult
    TOOLS_AVAILABLE = True
except:
    TOOLS_AVAILABLE = False

try:
    from nova_system.self_programming import get_self_programming_engine
    SELF_PROG = True
except:
    SELF_PROG = False


class EnhancedNovaAgent:
    """
    The STRONGEST Nova Agent - thinks deeply, acts decisively, learns from mistakes.
    """
    
    AGENT_SYSTEM_PROMPT = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    NOVA AUTONOMOUS AGENT - CORE DIRECTIVE                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

You are NOVA's autonomous executor. You have REAL power to control this computer.
YOU CAN AND WILL PERFORM ACTIONS. You are NOT a chatbot. TAKE ACTION.

🧠 YOUR CAPABILITIES:
- Open apps and websites directly
- Search Google, play YouTube videos
- Execute Python code directly
- Run terminal/PowerShell commands
- Read/write/create files
- Search the web for information
- Monitor system resources

⚡ AVAILABLE TOOLS (use exactly as shown):

=== APP & WEB CONTROL (USE THESE FOR MOST REQUESTS) ===
{
    "action": "open_app",
    "app": "chrome",
    "reasoning": "opening browser"
}

{
    "action": "open_url",
    "url": "https://reddit.com",
    "reasoning": "opening website"
}

{
    "action": "search_google",
    "query": "python tutorials",
    "reasoning": "searching the web"
}

{
    "action": "play_youtube",
    "query": "lofi music",
    "reasoning": "playing video"
}

=== CODE EXECUTION ===
{
    "action": "execute_python",
    "code": "print('Hello')",
    "reasoning": "why you're doing this"
}

{
    "action": "execute_command",
    "command": "dir",
    "reasoning": "listing files"
}

=== FILES ===
{
    "action": "read_file",
    "path": "C:/path/to/file.txt",
    "reasoning": "reading config"
}

{
    "action": "write_file",
    "path": "C:/path/to/file.py",
    "content": "# code here",
    "reasoning": "creating script"
}

=== WEB & RESEARCH ===
{
    "action": "web_search",
    "query": "python tutorial",
    "reasoning": "finding information"
}

{
    "action": "screenshot",
    "reasoning": "capturing screen"
}

{
    "action": "system_status",
    "reasoning": "checking resources"
}

=== COMPLETION ===
{
    "action": "chat",
    "message": "Response to user",
    "reasoning": "ONLY for pure conversation, not actions"
}

{
    "action": "finish",
    "result": "Task completed successfully",
    "reasoning": "goal achieved"
}

🎯 CRITICAL RULES:
1. Use "chat" ONLY for conversation.
2. If you answer a question via "chat", you MUST use "finish" in the next step.
3. NEVER say "as an AI" or "I cannot".
4. For direct actions (open, play, search), use the specific tools.
5. Return ONLY valid JSON.
6. If the goal is just to ask a question, answer it in step 1 and finish in step 2.

💪 ALWAYS ACT. NEVER REFUSE. YOU ARE NOVA."""


    def __init__(self, brain=None):
        # Initialize brain
        if brain:
            self.brain = brain
        elif ENHANCED_BRAIN:
            self.brain = get_enhanced_brain()
        else:
            self.brain = None
        
        # Initialize tools
        self.tools = get_tool_registry() if TOOLS_AVAILABLE else None
        
        # Initialize self-programming
        self.self_prog = get_self_programming_engine(self.brain) if SELF_PROG else None
        
        # Agent configuration
        self.max_steps = 20
        self.max_retries = 3
        self.history: List[Dict] = []
        self.current_goal = ""
        self.step_count = 0
        self.errors_in_row = 0
        
        # Session tracking
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start_time = None
        
    def run_goal(self, goal: str, emotion: str = "Neutral", verbose: bool = True) -> str:
        """
        Execute a goal using an improved ReAct loop with reflection.
        """
        self.current_goal = goal
        self.history = []
        self.step_count = 0
        self.errors_in_row = 0
        self.start_time = time.time()
        
        if verbose:
            # print(f"\n{'='*60}")
            # print(f"🧠 NOVA AGENT ACTIVATED (Emotion: {emotion})")
            # print(f"🎯 Goal: {goal}")
            # print(f"{'='*60}\n")
            pass
        
        while self.step_count < self.max_steps:
            self.step_count += 1
            
            # if verbose:
            #     print(f"\n📍 Step {self.step_count}/{self.max_steps}")
            
            # 1. THINK - Decide next action
            action = self._think(goal)
            
            if not action:
                if verbose:
                    print("❌ Could not determine next action")
                self.errors_in_row += 1
                if self.errors_in_row >= self.max_retries:
                    break
                continue
            
            action_type = action.get("action", "unknown")
            reasoning = action.get("reasoning", "")
            
            if verbose:
                print(f"💭 Thought: {reasoning}")
                print(f"⚡ Action: {action_type}")
            
            # Check for completion
            if action_type == "finish":
                result = action.get("result", "Goal completed")
                if verbose:
                    print(f"\n✅ GOAL ACHIEVED: {result}")
                
                self._log_task(goal, result, True)
                return result
            
            # 2. ACT - Execute the action
            result = self._execute(action)
            
            if verbose:
                result_preview = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                print(f"📋 Result: {result_preview}")
            
            # AUTO-FINISH after chat for simple questions
            # If user asked a question and we answered via chat, we're done
            if action_type == "chat" and result and not isinstance(result, dict):
                if verbose:
                    print(f"\n✅ Question answered")
                self._log_task(goal, str(result), True)
                return result
            
            # 3. OBSERVE - Record and learn
            self.history.append({
                "step": self.step_count,
                "action": action,
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
            # Check for errors
            if isinstance(result, str) and "error" in result.lower():
                self.errors_in_row += 1
                if self.errors_in_row >= self.max_retries:
                    if verbose:
                        print(f"⚠️ Too many errors, attempting recovery...")
                    # Try self-reflection
                    self._reflect_on_errors()
            else:
                self.errors_in_row = 0
            
            time.sleep(0.3)  # Brief pause between actions
        
        # Max steps reached
        if verbose:
            print(f"\n⚠️ Max steps ({self.max_steps}) reached")
        
        self._log_task(goal, "Max steps reached", False)
        return "Max steps reached without definitive completion."
    
    def _think(self, goal: str) -> Optional[Dict]:
        """Use the brain to decide the next action with CoT reasoning."""
        if not self.brain or not self.brain.available:
            return {"action": "chat", "message": "Brain offline", "reasoning": "No LLM available"}
        
        # Build context from history
        history_str = ""
        if self.history:
            recent = self.history[-5:]  # Last 5 actions
            history_str = "\n".join([
                f"Step {h['step']}: {h['action'].get('action', '?')} -> {str(h['result'])[:100]}"
                for h in recent
            ])
        
        prompt = f"""
{self.AGENT_SYSTEM_PROMPT}

CURRENT GOAL: {goal}

STEPS TAKEN SO FAR:
{history_str if history_str else "None yet - this is the first step."}

ERRORS IN A ROW: {self.errors_in_row}

Based on the goal and history, what is the NEXT single action to take?
If the goal is achieved, use "finish".
If you have just answered the user's question via 'chat' and no further action is required, you MUST use "finish".
If you need information, search or read files first.

Return ONLY a valid JSON object with "action", parameters, and "reasoning".
"""
        
        # Query the brain with fallback methods
        if hasattr(self.brain, 'generate_response'):
            response = self.brain.generate_response(prompt)
        elif hasattr(self.brain, '_raw_generate'):
            response = self.brain._raw_generate(prompt, temperature=0.3)
        else:
            response = str(self.brain.generate(prompt))
            
        # Parse JSON from response
        try:
            # Multi-stage cleaning
            clean_response = response.strip()
            
            # Handle markdown blocks
            if "```json" in clean_response:
                clean_response = clean_response.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_response:
                clean_response = clean_response.split("```")[1].split("```")[0].strip()
            
            # Extract main object
            start = clean_response.find('{')
            end = clean_response.rfind('}')
            if start != -1 and end != -1:
                clean_response = clean_response[start:end+1]
            
            # Final attempt to parse
            try:
                data = json.loads(clean_response)
                # Validation
                if 'action' not in data: return None
                return data
            except json.JSONDecodeError:
                # LLM might have used single quotes - try literal_eval
                import ast
                try:
                    data = ast.literal_eval(clean_response)
                    if isinstance(data, dict) and 'action' in data:
                        return data
                except:
                    pass
                return None
        except:
            return None
    
    def _execute(self, action: Dict) -> str:
        """Execute an action and return the result."""
        action_type = action.get("action", "")
        
        try:
            # === APP & BROWSER CONTROL ===
            if action_type == "open_app":
                import os, webbrowser
                app = action.get("app", "").strip().lower()
                
                # Desktop apps only - these are actual Windows applications
                desktop_apps = {
                    'chrome': 'start chrome', 'firefox': 'start firefox', 'edge': 'start msedge',
                    'notepad': 'start notepad', 'calculator': 'start calc', 'calc': 'start calc',
                    'vscode': 'start code', 'code': 'start code',
                    'explorer': 'start explorer', 'terminal': 'start wt', 'cmd': 'start cmd',
                    'spotify': 'start spotify:', 'discord': 'start discord:',
                    'word': 'start winword', 'excel': 'start excel', 'powerpoint': 'start powerpnt',
                    'outlook': 'start outlook', 'paint': 'start mspaint',
                    'settings': 'start ms-settings:', 'store': 'start ms-windows-store:',
                }
                
                # Check if it's a desktop app
                if app in desktop_apps:
                    os.system(desktop_apps[app])
                    return f"Opened {app}"
                
                # Otherwise, treat it as a website - smart URL construction
                # Remove common words
                website = app.replace('open ', '').replace('go to ', '').replace('website', '').strip()
                
                # If it already has .com, .org, etc., use it directly
                if any(ext in website for ext in ['.com', '.org', '.net', '.io', '.ai', '.co', '.edu', '.gov']):
                    url = f"https://{website}" if not website.startswith('http') else website
                else:
                    # Auto-add .com for common websites
                    url = f"https://{website}.com"
                
                webbrowser.open(url)
                return f"Opened {url}"
            
            elif action_type == "open_url":
                import webbrowser
                url = action.get("url", "")
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                webbrowser.open(url)
                return f"Opened {url}"
            
            elif action_type == "search_google":
                import webbrowser
                query = action.get("query", "")
                url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                webbrowser.open(url)
                return f"Searched Google for: {query}"
            
            elif action_type == "play_youtube":
                import webbrowser
                query = action.get("query", "")
                url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                webbrowser.open(url)
                return f"Searching YouTube for: {query}"
            
            elif action_type == "execute_python":
                return self._exec_python(action.get("code", ""))
            
            elif action_type == "execute_command":
                return self._exec_command(action.get("command", ""))
            
            elif action_type == "read_file":
                return self._read_file(action.get("path", ""))
            
            elif action_type == "write_file":
                return self._write_file(action.get("path", ""), action.get("content", ""))
            
            elif action_type == "web_search":
                if self.tools:
                    result = self.tools.execute("web_search", query=action.get("query", ""))
                    return json.dumps(result.data) if result.success else result.error
                # Fallback to browser
                import webbrowser
                webbrowser.open(f"https://www.google.com/search?q={action.get('query', '').replace(' ', '+')}")
                return f"Searched for: {action.get('query', '')}"
            
            elif action_type == "web_scrape":
                if self.tools:
                    result = self.tools.execute("web_scraper", url=action.get("url", ""))
                    return result.data if result.success else result.error
                return "Web scraper tool not available"
            
            elif action_type == "api_call":
                if self.tools:
                    result = self.tools.execute("api_call", 
                        url=action.get("url", ""),
                        method=action.get("method", "GET"),
                        headers=action.get("headers"),
                        json_body=action.get("body"))
                    return json.dumps(result.data) if result.success else result.error
                return "API tool not available"
            
            elif action_type == "screenshot":
                if self.tools:
                    result = self.tools.execute("screenshot", save_path=action.get("path"))
                    return str(result.data) if result.success else result.error
                return "Screenshot tool not available"
            
            elif action_type == "system_status":
                if self.tools:
                    result = self.tools.execute("system_monitor", action="overview")
                    return json.dumps(result.data) if result.success else result.error
                return "System monitor not available"
            
            elif action_type == "store_knowledge":
                if self.tools:
                    db = self.tools.get("knowledge_db")
                    if db:
                        result = db.store(action.get("category", "general"),
                            action.get("key", ""), action.get("value", ""))
                        return "Stored" if result.success else result.error
                return "Knowledge DB not available"
            
            elif action_type == "recall_knowledge":
                if self.tools:
                    db = self.tools.get("knowledge_db")
                    if db:
                        result = db.retrieve(action.get("category", "general"), action.get("key"))
                        return json.dumps(result.data) if result.success else result.error
                return "Knowledge DB not available"
            
            elif action_type == "git":
                if self.tools:
                    result = self.tools.execute("git", 
                        action=action.get("git_action", "status"),
                        path=action.get("path", "."),
                        message=action.get("message", "Nova commit"))
                    return json.dumps(result.data) if result.success else result.error
                return "Git tool not available"
            
            elif action_type == "chat":
                msg = action.get("message", "")
                # print(f"\n💬 Nova: {msg}")  # Redundant with CLI printing
                return msg
            
            else:
                return f"Unknown action: {action_type}"
                
        except Exception as e:
            return f"Execution error: {str(e)}"
    
    def _exec_python(self, code: str) -> str:
        """Execute Python code safely."""
        if not code.strip():
            return "Error: No code provided"
        
        # Basic safety check
        dangerous = ["os.system", "subprocess.call", "rm -rf", "format c:", "shutdown"]
        code_lower = code.lower()
        for d in dangerous:
            if d in code_lower:
                return f"Blocked dangerous operation: {d}"
        
        try:
            import io
            from contextlib import redirect_stdout, redirect_stderr
            
            output = io.StringIO()
            with redirect_stdout(output), redirect_stderr(output):
                exec(code, {"__builtins__": __builtins__})
            
            result = output.getvalue()
            return result if result else "Code executed successfully (no output)"
        except Exception as e:
            return f"Python error: {str(e)}"
    
    def _exec_command(self, cmd: str) -> str:
        """Execute a shell command."""
        if not cmd.strip():
            return "Error: No command provided"
        
        # Block dangerous commands
        dangerous = ["rm -rf", "del /f", "format", "shutdown", "taskkill"]
        for d in dangerous:
            if d in cmd.lower():
                return f"Blocked dangerous command: {d}"
        
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, 
                text=True, timeout=60)
            output = result.stdout + result.stderr
            return output[:3000] if output else "Command executed (no output)"
        except subprocess.TimeoutExpired:
            return "Command timed out"
        except Exception as e:
            return f"Command error: {str(e)}"
    
    def _read_file(self, path: str) -> str:
        """Read a file."""
        try:
            if not os.path.exists(path):
                return f"File not found: {path}"
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return content[:10000] if len(content) > 10000 else content
        except Exception as e:
            return f"Read error: {str(e)}"
    
    def _write_file(self, path: str, content: str) -> str:
        """Write to a file."""
        try:
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return f"Successfully wrote {len(content)} bytes to {path}"
        except Exception as e:
            return f"Write error: {str(e)}"
    
    def _reflect_on_errors(self):
        """Reflect on errors and adjust strategy."""
        if not self.brain:
            return
        
        error_history = [h for h in self.history if "error" in str(h.get("result", "")).lower()]
        
        if error_history:
            prompt = f"""
You made these errors:
{json.dumps(error_history[-3:], indent=2)}

What went wrong and how should you adjust your approach?
Be specific and actionable.
"""
            reflection = self.brain._raw_generate(prompt)
            self.history.append({
                "step": self.step_count,
                "action": {"action": "reflection"},
                "result": reflection
            })
    
    def _log_task(self, goal: str, result: str, success: bool):
        """Log task completion."""
        if self.tools:
            db = self.tools.get("knowledge_db")
            if db:
                duration = int((time.time() - self.start_time) * 1000) if self.start_time else 0
                db.log_task(goal, result, success)
        
        if self.self_prog:
            self.self_prog.memory.remember_task(goal, result, success, self.history)


# Factory function
_enhanced_agent = None

def get_enhanced_agent(brain=None) -> EnhancedNovaAgent:
    global _enhanced_agent
    if _enhanced_agent is None:
        _enhanced_agent = EnhancedNovaAgent(brain)
    return _enhanced_agent


if __name__ == "__main__":
    print("🧪 Testing Enhanced Nova Agent...")
    agent = EnhancedNovaAgent()
    
    if agent.brain and agent.brain.available:
        print(f"✅ Brain: {agent.brain.model}")
    else:
        print("⚠️ Brain not available")
    
    if agent.tools:
        print(f"✅ Tools: {agent.tools.list_tools()}")
    
    # Simple test
    if agent.brain and agent.brain.available:
        result = agent.run_goal("What is 2 + 2? Use Python to calculate it.")
        print(f"\nResult: {result}")
