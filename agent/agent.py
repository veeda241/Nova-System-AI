#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA MCP Agent - Code Generation and Execution Agent
Uses Ollama LLM to generate Python code and execute it safely
"""

import os
import sys
import json
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools import (
    CreatePythonFileTool,
    ExecutePythonFileTool,
    ExecutePythonCodeTool,
    ReadFileTool,
    ListFilesTool,
    check_code_safety,
    WORKSPACE
)

# ═══════════════════════════════════════════════════════════════════════════════
# AGENT CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5-coder"

# System prompts for different modes
SYSTEM_PROMPTS = {
    "code_generator": """You are an expert Python code generator.

RULES:
1. Generate ONLY executable Python code - no explanations, no markdown.
2. The code must be complete and runnable.
3. Include all necessary imports at the top.
4. For plots, use plt.savefig('output.png') instead of plt.show().
5. Print results to stdout so they can be captured.
6. Handle errors gracefully with try/except.
7. Keep code concise but functional.

IMPORTANT: Output ONLY the Python code, nothing else.""",

    "code_with_plan": """You are an expert Python code generator with planning capabilities.

When given a task:
1. First output a brief PLAN (2-3 lines max)
2. Then output the Python code

Format:
PLAN:
- Step 1
- Step 2

CODE:
```python
# your code here
```

RULES:
- Code must be complete and executable
- Include all imports
- For plots, save to file instead of showing
- Print results to stdout""",

    "tool_caller": """You are an AI agent that uses tools to complete tasks.

Available tools:
- create_python_file: Create a Python file with code
- execute_python_file: Execute a Python file
- execute_python_code: Execute Python code directly
- read_file: Read file contents
- list_files: List files in workspace

To use a tool, output JSON:
{"tool": "tool_name", "arguments": {"arg1": "value1"}}

First generate code, then call the appropriate tool to execute it."""
}


# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class OllamaClient:
    """Simple Ollama API client."""
    
    def __init__(self, base_url: str = OLLAMA_URL):
        self.base_url = base_url
    
    def chat(self, model: str, messages: List[Dict], stream: bool = False) -> Dict:
        """Send a chat request to Ollama."""
        import urllib.request
        import json
        
        url = f"{self.base_url}/api/chat"
        data = json.dumps({
            "model": model,
            "messages": messages,
            "stream": stream
        }).encode()
        
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode())
                return result
        except Exception as e:
            return {"error": str(e)}
    
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        import urllib.request
        try:
            urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=5)
            return True
        except:
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# MCP AGENT
# ═══════════════════════════════════════════════════════════════════════════════

class MCPAgent:
    """
    MCP-style agent that generates and executes Python code.
    
    Workflow:
    1. User provides a prompt
    2. LLM generates Python code
    3. Code is saved to a file
    4. Code is executed safely
    5. Output is returned to user
    """
    
    def __init__(self, model: str = DEFAULT_MODEL, mode: str = "code_generator"):
        self.model = model
        self.mode = mode
        self.client = OllamaClient()
        self.history: List[Dict] = []
        
        # Tools
        self.create_file_tool = CreatePythonFileTool()
        self.execute_file_tool = ExecutePythonFileTool()
        self.execute_code_tool = ExecutePythonCodeTool()
        self.read_file_tool = ReadFileTool()
        self.list_files_tool = ListFilesTool()
    
    def set_model(self, model: str):
        """Set the LLM model to use."""
        self.model = model
    
    def set_mode(self, mode: str):
        """Set the agent mode."""
        if mode in SYSTEM_PROMPTS:
            self.mode = mode
    
    def run(self, prompt: str, auto_execute: bool = True) -> Dict[str, Any]:
        """
        Run the agent with a user prompt.
        
        Args:
            prompt: User's request/task
            auto_execute: Whether to automatically execute generated code
        
        Returns:
            Dict with code, file path, execution output, etc.
        """
        result = {
            "prompt": prompt,
            "success": False,
            "code": None,
            "plan": None,
            "filepath": None,
            "output": None,
            "errors": None,
            "timestamp": datetime.now().isoformat()
        }
        
        # Check if Ollama is available
        if not self.client.is_available():
            result["errors"] = "Ollama is not running. Start it with 'ollama serve'"
            return result
        
        # Step 1: Generate code using LLM
        print("🧠 Generating code...")
        
        system_prompt = SYSTEM_PROMPTS.get(self.mode, SYSTEM_PROMPTS["code_generator"])
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = self.client.chat(self.model, messages)
        
        if "error" in response:
            result["errors"] = f"LLM Error: {response['error']}"
            return result
        
        llm_output = response.get("message", {}).get("content", "")
        
        if not llm_output:
            result["errors"] = "LLM returned empty response"
            return result
        
        # Step 2: Parse the response (extract plan and code if present)
        code, plan = self._parse_response(llm_output)
        result["code"] = code
        result["plan"] = plan
        
        if not code:
            result["errors"] = "No code could be extracted from LLM response"
            result["raw_response"] = llm_output
            return result
        
        # Step 3: Create Python file
        print("📄 Creating file...")
        
        # Try to extract filename from code comment (e.g., # filename: test.py or # test.py)
        requested_filename = None
        first_line = code.split('\n')[0].strip() if code else ""
        if first_line.startswith('#'):
            potential_name = first_line.replace('#', '').strip()
            if potential_name.endswith('.py') and ' ' not in potential_name:
                requested_filename = potential_name
            elif 'filename:' in first_line.lower():
                requested_filename = first_line.lower().split('filename:')[1].strip()
        
        create_result = self.create_file_tool.execute(code=code, filename=requested_filename)
        
        if not create_result["success"]:
            result["errors"] = create_result.get("error", "Failed to create file")
            return result
        
        result["filepath"] = create_result["filepath"]
        print(f"   → {create_result['filepath']}")
        
        # Step 4: Execute if auto_execute is enabled
        if auto_execute:
            print("▶ Executing code...")
            
            exec_result = self.execute_file_tool.execute(
                filepath=create_result["filepath"],
                timeout=30
            )
            
            result["output"] = exec_result.get("output", "")
            result["errors"] = exec_result.get("errors", "")
            result["success"] = exec_result.get("success", False)
            result["return_code"] = exec_result.get("return_code", -1)
            
            if result["success"]:
                print("✅ Execution successful!")
            else:
                print(f"❌ Execution failed: {result['errors']}")
        else:
            result["success"] = True
            print("⏸ Code saved but not executed (auto_execute=False)")
        
        # Save to history
        self.history.append(result)
        
        return result
    
    def _parse_response(self, response: str) -> tuple[str, Optional[str]]:
        """
        Parse the LLM response to extract code and optional plan.
        
        Returns:
            (code, plan) tuple
        """
        plan = None
        code = response
        
        # Check for PLAN section
        if "PLAN:" in response:
            parts = response.split("CODE:", 1)
            if len(parts) == 2:
                plan_section = parts[0]
                code = parts[1]
                
                # Extract plan
                plan_match = re.search(r"PLAN:\s*\n([\s\S]*?)(?=CODE:|$)", plan_section)
                if plan_match:
                    plan = plan_match.group(1).strip()
        
        # Clean code - remove markdown blocks
        code = re.sub(r"```python\s*\n?", "", code)
        code = re.sub(r"```\s*\n?", "", code)
        code = code.strip()
        
        # Remove any leading text before actual Python code
        lines = code.split("\n")
        code_start = 0
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith(("import ", "from ", "def ", "class ", "#", "'''", '"""')) or \
               stripped == "" or \
               re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*\s*=", stripped):
                code_start = i
                break
        
        code = "\n".join(lines[code_start:])
        
        return code, plan
    
    def run_interactive(self):
        """Run the agent in interactive mode."""
        print("\n" + "=" * 60)
        print("       🚀 NOVA MCP Agent - Code Generation & Execution")
        print("=" * 60)
        print(f"Model: {self.model}")
        print(f"Mode: {self.mode}")
        print(f"Workspace: {WORKSPACE}")
        print("\nType your prompt and press Enter. Type 'exit' to quit.")
        print("Commands: /model, /mode, /history, /files, /clear")
        print("=" * 60 + "\n")
        
        while True:
            try:
                prompt = input("🧠 Prompt: ").strip()
                
                if not prompt:
                    continue
                
                if prompt.lower() in ["exit", "quit", "/exit", "/quit"]:
                    print("\n👋 Goodbye!")
                    break
                
                if prompt.startswith("/"):
                    self._handle_command(prompt)
                    continue
                
                # Run the agent
                result = self.run(prompt)
                
                print("\n" + "-" * 40)
                
                if result["plan"]:
                    print("📋 Plan:")
                    print(result["plan"])
                    print()
                
                print("📄 Generated Code:")
                print("-" * 40)
                if result["code"]:
                    # Show first 30 lines
                    lines = result["code"].split("\n")
                    for line in lines[:30]:
                        print(line)
                    if len(lines) > 30:
                        print(f"... ({len(lines) - 30} more lines)")
                print("-" * 40)
                
                if result["filepath"]:
                    print(f"\n📁 File: {result['filepath']}")
                
                if result["output"]:
                    print("\n▶ Output:")
                    print(result["output"])
                
                if result["errors"] and not result["success"]:
                    print(f"\n❌ Errors:\n{result['errors']}")
                
                print("\n")
                
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Type 'exit' to quit.")
            except Exception as e:
                print(f"\n❌ Error: {e}\n")
    
    def _handle_command(self, cmd: str):
        """Handle agent commands."""
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""
        
        if command == "/model":
            if arg:
                self.model = arg
                print(f"✓ Model set to: {self.model}")
            else:
                print(f"Current model: {self.model}")
        
        elif command == "/mode":
            if arg and arg in SYSTEM_PROMPTS:
                self.mode = arg
                print(f"✓ Mode set to: {self.mode}")
            else:
                print(f"Current mode: {self.mode}")
                print(f"Available modes: {list(SYSTEM_PROMPTS.keys())}")
        
        elif command == "/history":
            if not self.history:
                print("No history yet.")
            else:
                print(f"\n📜 History ({len(self.history)} items):")
                for i, item in enumerate(self.history[-5:], 1):
                    status = "✓" if item["success"] else "✗"
                    print(f"  {i}. [{status}] {item['prompt'][:50]}...")
        
        elif command == "/files":
            result = self.list_files_tool.execute()
            if result["success"]:
                print(f"\n📁 Workspace files ({result['count']}):")
                for f in result["files"]:
                    print(f"  - {f['name']} ({f['size']} bytes)")
            else:
                print("No files in workspace.")
        
        elif command == "/clear":
            self.history = []
            print("✓ History cleared.")
        
        elif command == "/help":
            print("""
Commands:
  /model [name]  - Get/set LLM model
  /mode [mode]   - Get/set agent mode
  /history       - Show recent history
  /files         - List workspace files
  /clear         - Clear history
  /help          - Show this help
  exit           - Exit agent
""")
        else:
            print(f"Unknown command: {command}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Run the MCP Agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description="NOVA MCP Agent")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help="Ollama model to use")
    parser.add_argument("--mode", default="code_generator", choices=list(SYSTEM_PROMPTS.keys()))
    parser.add_argument("--prompt", "-p", help="Single prompt to run (non-interactive)")
    parser.add_argument("--no-execute", action="store_true", help="Don't execute generated code")
    args = parser.parse_args()
    
    agent = MCPAgent(model=args.model, mode=args.mode)
    
    if args.prompt:
        # Single prompt mode
        result = agent.run(args.prompt, auto_execute=not args.no_execute)
        
        print("\n" + "=" * 40)
        print("📄 Generated Code:")
        print(result.get("code", "No code generated"))
        print("=" * 40)
        
        if result.get("output"):
            print("\n▶ Output:")
            print(result["output"])
        
        if result.get("errors") and not result["success"]:
            print(f"\n❌ Errors:\n{result['errors']}")
            sys.exit(1)
    else:
        # Interactive mode
        agent.run_interactive()


if __name__ == "__main__":
    main()
