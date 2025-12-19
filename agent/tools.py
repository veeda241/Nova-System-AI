#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA MCP Tools - File System and Code Execution Tools
Model Context Protocol (MCP) style tools for the NOVA Agent
"""

import subprocess
import uuid
import os
import sys
import re
from typing import Dict, Any, Optional
from datetime import datetime

# Workspace directory for generated files
WORKSPACE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workspace")
os.makedirs(WORKSPACE, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY CHECKS
# ═══════════════════════════════════════════════════════════════════════════════

BLOCKED_PATTERNS = [
    r"os\.system\s*\(",
    r"subprocess\.call\s*\(",
    r"subprocess\.Popen\s*\(",
    r"exec\s*\(",
    r"eval\s*\(",
    r"__import__\s*\(",
    r"rm\s+-rf",
    r"rmdir\s+/s",
    r"del\s+/f",
    r"format\s+[a-zA-Z]:",
    r"shutdown",
    r"taskkill",
    r"\.remove\s*\(",
    r"\.rmtree\s*\(",
    r"open\s*\([^)]*['\"]w['\"]",  # Block file writes outside workspace
]

ALLOWED_IMPORTS = [
    "math", "random", "datetime", "time", "json", "re", "collections",
    "itertools", "functools", "operator", "string", "textwrap",
    "numpy", "pandas", "matplotlib", "seaborn", "plotly",
    "scipy", "sklearn", "requests", "beautifulsoup4", "bs4",
    "PIL", "cv2", "torch", "tensorflow", "keras"
]


def check_code_safety(code: str) -> tuple[bool, str]:
    """
    Check if the generated code is safe to execute.
    Returns (is_safe, reason).
    """
    # Check for blocked patterns
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return False, f"Blocked pattern detected: {pattern}"
    
    # Check for suspicious file operations outside workspace
    if "open(" in code:
        # Allow only relative paths or workspace paths
        file_opens = re.findall(r"open\s*\(\s*['\"]([^'\"]+)['\"]", code)
        for path in file_opens:
            if os.path.isabs(path) and "workspace" not in path.lower():
                return False, f"Absolute path outside workspace: {path}"
    
    return True, "Code passed safety checks"


# ═══════════════════════════════════════════════════════════════════════════════
# MCP TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

class MCPTool:
    """Base class for MCP tools."""
    name: str = ""
    description: str = ""
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError


class CreatePythonFileTool(MCPTool):
    """Tool to create a Python file from generated code."""
    name = "create_python_file"
    description = "Create a Python file with the given code"
    
    def execute(self, code: str, filename: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a Python file with the given code.
        
        Args:
            code: Python code to write to the file
            filename: Optional filename (will be auto-generated if not provided)
        
        Returns:
            Dict with filepath and status
        """
        # Clean code (remove markdown code blocks if present)
        code = self._clean_code(code)
        
        # Safety check
        is_safe, reason = check_code_safety(code)
        if not is_safe:
            return {
                "success": False,
                "error": f"Unsafe code blocked: {reason}",
                "filepath": None
            }
        
        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_{timestamp}_{uuid.uuid4().hex[:6]}.py"
        
        filepath = os.path.join(WORKSPACE, filename)
        
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
            
            return {
                "success": True,
                "filepath": filepath,
                "filename": filename,
                "code_length": len(code)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "filepath": None
            }
    
    def _clean_code(self, code: str) -> str:
        """Remove markdown code blocks and clean up the code."""
        # Remove ```python ... ``` blocks
        code = re.sub(r"```python\s*\n?", "", code)
        code = re.sub(r"```\s*\n?", "", code)
        
        # Remove leading/trailing whitespace
        code = code.strip()
        
        return code


class ExecutePythonFileTool(MCPTool):
    """Tool to execute a Python file safely."""
    name = "execute_python_file"
    description = "Execute a Python file and return output"
    
    def execute(self, filepath: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute a Python file safely with timeout.
        
        Args:
            filepath: Path to the Python file
            timeout: Maximum execution time in seconds
        
        Returns:
            Dict with output, errors, and return code
        """
        if not os.path.exists(filepath):
            return {
                "success": False,
                "error": f"File not found: {filepath}",
                "output": "",
                "return_code": -1
            }
        
        # Read and check code safety again before execution
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
        
        is_safe, reason = check_code_safety(code)
        if not is_safe:
            return {
                "success": False,
                "error": f"Unsafe code blocked: {reason}",
                "output": "",
                "return_code": -1
            }
        
        try:
            # Execute with timeout
            result = subprocess.run(
                [sys.executable, filepath],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=WORKSPACE,  # Run in workspace directory
                env={**os.environ, "PYTHONIOENCODING": "utf-8"}
            )
            
            output = result.stdout
            errors = result.stderr
            
            return {
                "success": result.returncode == 0,
                "output": output,
                "errors": errors,
                "return_code": result.returncode,
                "filepath": filepath
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Execution timed out after {timeout} seconds",
                "output": "",
                "return_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "return_code": -1
            }


class ExecutePythonCodeTool(MCPTool):
    """Tool to execute Python code directly (without creating a file)."""
    name = "execute_python_code"
    description = "Execute Python code directly and return output"
    
    def execute(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Execute Python code directly.
        
        Args:
            code: Python code to execute
            timeout: Maximum execution time in seconds
        
        Returns:
            Dict with output, errors, and return code
        """
        # Clean code
        code = re.sub(r"```python\s*\n?", "", code)
        code = re.sub(r"```\s*\n?", "", code)
        code = code.strip()
        
        # Safety check
        is_safe, reason = check_code_safety(code)
        if not is_safe:
            return {
                "success": False,
                "error": f"Unsafe code blocked: {reason}",
                "output": "",
                "return_code": -1
            }
        
        try:
            result = subprocess.run(
                [sys.executable, "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=WORKSPACE,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"}
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
                "return_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Execution timed out after {timeout} seconds",
                "output": "",
                "return_code": -1
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
                "return_code": -1
            }


class ReadFileTool(MCPTool):
    """Tool to read file contents."""
    name = "read_file"
    description = "Read the contents of a file"
    
    def execute(self, filepath: str) -> Dict[str, Any]:
        """Read file contents."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            return {
                "success": True,
                "content": content,
                "filepath": filepath,
                "size": len(content)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "content": ""
            }


class ListFilesTool(MCPTool):
    """Tool to list files in workspace."""
    name = "list_files"
    description = "List files in the workspace directory"
    
    def execute(self, pattern: str = "*") -> Dict[str, Any]:
        """List files in workspace."""
        import glob
        
        try:
            files = glob.glob(os.path.join(WORKSPACE, pattern))
            file_info = []
            for f in files:
                stat = os.stat(f)
                file_info.append({
                    "name": os.path.basename(f),
                    "path": f,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            
            return {
                "success": True,
                "files": file_info,
                "count": len(file_info)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "files": []
            }


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

TOOLS = {
    "create_python_file": CreatePythonFileTool(),
    "execute_python_file": ExecutePythonFileTool(),
    "execute_python_code": ExecutePythonCodeTool(),
    "read_file": ReadFileTool(),
    "list_files": ListFilesTool(),
}


def get_tool(name: str) -> Optional[MCPTool]:
    """Get a tool by name."""
    return TOOLS.get(name)


def execute_tool(name: str, **kwargs) -> Dict[str, Any]:
    """Execute a tool by name with given arguments."""
    tool = get_tool(name)
    if tool is None:
        return {"success": False, "error": f"Unknown tool: {name}"}
    return tool.execute(**kwargs)


def get_tools_description() -> str:
    """Get a description of all available tools for the LLM."""
    desc = "Available tools:\n"
    for name, tool in TOOLS.items():
        desc += f"- {name}: {tool.description}\n"
    return desc


if __name__ == "__main__":
    # Test the tools
    print("Testing MCP Tools...")
    
    # Test create file
    create_tool = CreatePythonFileTool()
    result = create_tool.execute(code="print('Hello from MCP!')")
    print(f"Create file: {result}")
    
    if result["success"]:
        # Test execute file
        exec_tool = ExecutePythonFileTool()
        result = exec_tool.execute(filepath=result["filepath"])
        print(f"Execute file: {result}")
    
    # Test direct execution
    exec_code = ExecutePythonCodeTool()
    result = exec_code.execute(code="print(2 + 2)")
    print(f"Execute code: {result}")
