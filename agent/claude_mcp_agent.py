#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Agent - Model Context Protocol Agent for Coding Tasks
==========================================================
Uses Ollama local LLMs with MCP tools for autonomous code generation,
file operations, and task execution.
"""

import os
import json
import re
import requests
from typing import List, Dict, Any, Optional
from agent.tools import (
    CreatePythonFileTool,
    ExecutePythonFileTool,
    ExecutePythonCodeTool,
    ReadFileTool,
    ListFilesTool,
    SearchFilesTool,
    WORKSPACE
)


# Ollama configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "nova")  # Custom NOVA model with MCP tools


class ClaudeMCPAgent:
    """Ollama-powered MCP agent with tool execution capabilities."""
    
    def __init__(self, model: str = None, ollama_url: str = None):
        """
        Initialize MCP Agent with Ollama.
        
        Args:
            model: Ollama model to use (default: qwen2.5-coder)
            ollama_url: Ollama API URL (default: http://localhost:11434)
        """
        self.model = model or DEFAULT_MODEL
        self.ollama_url = ollama_url or OLLAMA_URL
        self.max_iterations = 10
        
        # Initialize MCP tools
        self._init_tools()
        
    def _init_tools(self):
        """Initialize MCP tools."""
        self.tools = {
            'create_python_file': CreatePythonFileTool(),
            'execute_python_file': ExecutePythonFileTool(),
            'execute_python_code': ExecutePythonCodeTool(),
            'read_file': ReadFileTool(),
            'list_files': ListFilesTool(),
            'search_files': SearchFilesTool()
        }
        
    def _get_tools_description(self) -> str:
        """Get tool descriptions for the system prompt."""
        return """You have access to the following tools:

1. **create_python_file(code, filename)** - Create a new Python file in the workspace
   - code: Python code to write (required)
   - filename: Name of the file (e.g., "script.py") (optional)

2. **execute_python_file(filepath)** - Execute a Python file from the workspace
   - filepath: Full path or filename of the file to run

3. **execute_python_code(code)** - Execute Python code directly
   - code: Python code to execute

4. **read_file(filepath)** - Read contents of a file
   - filepath: Path to the file to read

5. **list_files(pattern)** - List files in the workspace
   - pattern: Optional glob pattern (default: "*")

6. **search_files(pattern)** - Search for files by pattern
   - pattern: Search pattern (e.g., "*.py")

To use a tool, respond with a JSON block in this format:
```tool
{"tool": "tool_name", "args": {"arg1": "value1", "arg2": "value2"}}
```

After using a tool, you will receive the result and can continue your work.
When the task is complete, provide a summary without using any tool blocks."""
        
    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> str:
        """Execute a tool and return the result."""
        try:
            tool = self.tools.get(tool_name)
            if not tool:
                return f"Error: Unknown tool '{tool_name}'"
            
            result = tool.execute(**tool_input)
            
            # Result is a dict with 'success' key
            if isinstance(result, dict):
                if result.get("success"):
                    # Format the successful result
                    output_parts = []
                    for key, value in result.items():
                        if key != "success":
                            output_parts.append(f"{key}: {value}")
                    return "Success! " + ", ".join(output_parts)
                else:
                    return f"Error: {result.get('error', 'Tool execution failed')}"
            else:
                return str(result)
                
        except Exception as e:
            return f"Error executing tool: {str(e)}"
    
    def _parse_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse tool call from LLM response."""
        # Look for ```tool blocks
        tool_pattern = r'```tool\s*\n?(.*?)\n?```'
        matches = re.findall(tool_pattern, response, re.DOTALL)
        
        if matches:
            try:
                return json.loads(matches[0].strip())
            except json.JSONDecodeError:
                pass
        
        # Also try ```json blocks with tool structure
        json_pattern = r'```json\s*\n?(.*?)\n?```'
        matches = re.findall(json_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                data = json.loads(match.strip())
                if "tool" in data:
                    return data
            except json.JSONDecodeError:
                continue
                
        return None
    
    def _call_ollama(self, messages: List[Dict[str, str]], system: str) -> str:
        """Call Ollama API for chat completion."""
        try:
            payload = {
                "model": self.model,
                "messages": [{"role": "system", "content": system}] + messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_predict": 2048
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json=payload,
                timeout=300  # 5 minutes for complex tasks
            )
            
            if response.status_code != 200:
                return f"❌ Ollama Error: {response.status_code} - {response.text}"
            
            result = response.json()
            return result.get("message", {}).get("content", "")
            
        except requests.exceptions.ConnectionError:
            return "❌ Cannot connect to Ollama. Make sure Ollama is running (ollama serve)."
        except requests.exceptions.Timeout:
            return "❌ Request timed out. The model might be loading or the query is complex."
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def process_query(self, query: str, system_context: Optional[str] = None) -> str:
        """
        Process a query using Ollama with MCP tools.
        
        Args:
            query: User query/task
            system_context: Optional additional system context
            
        Returns:
            Final response text
        """
        # Build system prompt
        base_system = """You are a coding assistant with access to file system tools.
You can create, read, execute Python files, and search the workspace.
When given a coding task:
1. Break it down into steps
2. Use tools to implement the solution
3. Test your code by executing it
4. Provide clear feedback

The workspace directory is your working environment."""

        tools_desc = self._get_tools_description()
        system_prompt = f"{base_system}\n\n{tools_desc}"
        
        if system_context:
            system_prompt = f"{system_context}\n\n{system_prompt}"
        
        # Build conversation history
        messages = [{"role": "user", "content": query}]
        
        iteration = 0
        final_response = ""
        
        print(f"[🤖] Using Ollama model: {self.model}")
        
        while iteration < self.max_iterations:
            iteration += 1
            
            # Call Ollama
            response = self._call_ollama(messages, system_prompt)
            
            # Check for errors
            if response.startswith("❌"):
                return response
            
            # Add assistant response to history
            messages.append({"role": "assistant", "content": response})
            
            # Check for tool calls
            tool_call = self._parse_tool_call(response)
            
            if tool_call:
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args", {})
                
                print(f"[🔧] Executing tool: {tool_name}")
                print(f"[📥] Args: {json.dumps(tool_args, indent=2)}")
                
                # Execute the tool
                tool_result = self._execute_tool(tool_name, tool_args)
                
                # Truncate output for display
                display_output = tool_result[:300] + "..." if len(tool_result) > 300 else tool_result
                print(f"[📤] Result: {display_output}")
                
                # Add tool result to conversation
                messages.append({
                    "role": "user",
                    "content": f"Tool result for {tool_name}:\n```\n{tool_result}\n```\n\nContinue with the task or provide a summary if complete."
                })
                
                continue
            else:
                # No tool call - this is the final response
                final_response = response
                break
        
        if iteration >= self.max_iterations:
            return f"⚠️ Maximum iterations reached.\n\nLast response:\n{final_response}"
        
        return final_response

    def check_ollama_status(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]
                
                if self.model.split(":")[0] in model_names:
                    return True
                else:
                    print(f"⚠️ Model '{self.model}' not found. Available: {model_names}")
                    return False
            return False
        except:
            return False
    
    def run(self, prompt: str) -> Dict[str, Any]:
        """
        Run the agent on a prompt and return structured results.
        This is the main entry point used by the CLI.
        
        Args:
            prompt: User's task/prompt
            
        Returns:
            Dict with keys: success, response, code, filepath, data
        """
        result = {
            "success": False,
            "response": "",
            "code": None,
            "filepath": None,
            "data": {}
        }
        
        try:
            # Process the query
            response = self.process_query(prompt)
            
            if response.startswith("❌"):
                result["response"] = response
                return result
            
            result["success"] = True
            result["response"] = response
            
            # Extract code blocks if present
            code_pattern = r'```(?:python)?\s*\n(.*?)\n```'
            code_matches = re.findall(code_pattern, response, re.DOTALL)
            if code_matches:
                result["code"] = code_matches[-1]  # Last code block
            
            # Extract file path if mentioned
            filepath_pattern = r'(?:created|saved|wrote|file)[:\s]+[`\'"]?([^\s`\'"]+\.py)[`\'"]?'
            filepath_matches = re.findall(filepath_pattern, response, re.IGNORECASE)
            if filepath_matches:
                result["filepath"] = filepath_matches[-1]
                result["data"]["filepath"] = filepath_matches[-1]
            
            return result
            
        except Exception as e:
            result["response"] = f"❌ Agent error: {str(e)}"
            return result
    
    def run_goal(self, goal: str, emotion: str = None) -> str:
        """
        Run the agent on a goal (alias for process_query with emotion context).
        
        Args:
            goal: User's goal/task
            emotion: Optional emotional context
            
        Returns:
            Response text
        """
        context = None
        if emotion:
            context = f"The user's current mood appears to be: {emotion}. Be empathetic."
        
        return self.process_query(goal, system_context=context)


# Standalone test
if __name__ == "__main__":
    print("🤖 MCP Agent Test (Ollama)")
    print("=" * 50)
    
    agent = ClaudeMCPAgent()
    
    # Check Ollama status
    if not agent.check_ollama_status():
        print(f"❌ Ollama not running or model '{agent.model}' not available.")
        print("   Run: ollama serve")
        print(f"   Then: ollama pull {agent.model}")
    else:
        print(f"✅ Ollama ready with model: {agent.model}")
        
        # Test query
        query = "Create a Python file called 'hello.py' that prints 'Hello from MCP Agent!', then execute it."
        print(f"\n📝 Query: {query}\n")
        
        response = agent.process_query(query)
        print(f"\n✅ Response:\n{response}")
