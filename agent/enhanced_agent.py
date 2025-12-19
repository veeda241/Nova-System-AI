#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Enhanced MCP Agent - Inspired by Gemini CLI Architecture
A powerful code generation and execution agent using local LLMs
"""

import os
import sys
import json
import re
import subprocess
import uuid
import hashlib
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.live import Live
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5-coder"
WORKSPACE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "workspace")
os.makedirs(WORKSPACE_DIR, exist_ok=True)

# ═══════════════════════════════════════════════════════════════════════════════
# TOOL TYPES (Inspired by Gemini CLI's Kind enum)
# ═══════════════════════════════════════════════════════════════════════════════

class ToolKind(Enum):
    READ = "read"          # Read-only operations
    WRITE = "write"        # Write/create operations
    EXECUTE = "execute"    # Execute code/commands
    SEARCH = "search"      # Search operations
    OTHER = "other"        # Other operations


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    output: str
    error: Optional[str] = None
    data: Any = None
    llm_content: Optional[str] = None  # Content for LLM
    return_display: Optional[str] = None  # Content for user display


@dataclass
class FunctionDeclaration:
    """Function declaration for LLM (similar to Gemini's FunctionDeclaration)."""
    name: str
    description: str
    parameters: Dict[str, Any]


# ═══════════════════════════════════════════════════════════════════════════════
# BASE TOOL (Inspired by Gemini CLI's BaseDeclarativeTool)
# ═══════════════════════════════════════════════════════════════════════════════

class BaseTool(ABC):
    """Abstract base class for all tools."""
    
    def __init__(
        self,
        name: str,
        display_name: str,
        description: str,
        kind: ToolKind,
        parameter_schema: Dict[str, Any],
        is_output_markdown: bool = False,
        can_update_output: bool = False
    ):
        self.name = name
        self.display_name = display_name
        self.description = description
        self.kind = kind
        self.parameter_schema = parameter_schema
        self.is_output_markdown = is_output_markdown
        self.can_update_output = can_update_output
    
    @property
    def schema(self) -> FunctionDeclaration:
        """Get the function declaration schema for the LLM."""
        return FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=self.parameter_schema
        )
    
    def validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Validate parameters. Return error message if invalid, None if valid."""
        required = self.parameter_schema.get("required", [])
        for req in required:
            if req not in params:
                return f"Missing required parameter: {req}"
        return None
    
    @abstractmethod
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        """Execute the tool with given parameters."""
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# SECURITY LAYER (Inspired by Gemini CLI's policy system)
# ═══════════════════════════════════════════════════════════════════════════════

class SecurityPolicy:
    """Security policy for code execution."""
    
    BLOCKED_PATTERNS = [
        r"os\.system\s*\(",
        r"subprocess\.call\s*\(",
        r"exec\s*\(",
        r"eval\s*\(",
        r"__import__\s*\(",
        r"rm\s+-rf",
        r"rmdir\s+/[sq]",
        r"del\s+/[fqs]",
        r"format\s+[a-zA-Z]:",
        r"shutdown",
        r"taskkill",
        r"\.rmtree\s*\(",
    ]
    
    ALLOWED_IMPORTS = [
        "math", "random", "datetime", "time", "json", "re", "collections",
        "itertools", "functools", "operator", "string", "textwrap", "os.path",
        "numpy", "pandas", "matplotlib", "seaborn", "plotly", "PIL",
        "scipy", "sklearn", "requests", "bs4"
    ]
    
    @classmethod
    def check_code_safety(cls, code: str) -> tuple[bool, str]:
        """Check if code is safe to execute."""
        for pattern in cls.BLOCKED_PATTERNS:
            if re.search(pattern, code, re.IGNORECASE):
                return False, f"Blocked pattern detected: {pattern}"
        return True, "Code passed safety checks"
    
    @classmethod
    def check_command_safety(cls, command: str) -> tuple[bool, str]:
        """Check if shell command is safe to execute."""
        dangerous_commands = ["rm -rf", "del /f", "format", "shutdown", "rd /s"]
        for dangerous in dangerous_commands:
            if dangerous.lower() in command.lower():
                return False, f"Dangerous command blocked: {dangerous}"
        return True, "Command passed safety checks"


# ═══════════════════════════════════════════════════════════════════════════════
# BUILT-IN TOOLS (Inspired by Gemini CLI's tool implementations)
# ═══════════════════════════════════════════════════════════════════════════════

class ReadFileTool(BaseTool):
    """Tool to read file contents."""
    
    def __init__(self):
        super().__init__(
            name="read_file",
            display_name="Read File",
            description="Read the contents of a file. Returns the file content as text.",
            kind=ToolKind.READ,
            parameter_schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to read"
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Optional starting line number (1-indexed)"
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Optional ending line number (1-indexed)"
                    }
                },
                "required": ["file_path"]
            }
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        file_path = params.get("file_path", "")
        start_line = params.get("start_line")
        end_line = params.get("end_line")
        
        try:
            if not os.path.exists(file_path):
                return ToolResult(False, "", f"File not found: {file_path}")
            
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            
            if start_line or end_line:
                start = (start_line or 1) - 1
                end = end_line or total_lines
                lines = lines[start:end]
            
            content = "".join(lines)
            
            return ToolResult(
                success=True,
                output=content,
                data={"total_lines": total_lines, "file_path": file_path},
                llm_content=f"File: {file_path} ({total_lines} lines)\n\n{content[:5000]}"
            )
        except Exception as e:
            return ToolResult(False, "", str(e))


class WriteFileTool(BaseTool):
    """Tool to write/create files."""
    
    def __init__(self):
        super().__init__(
            name="write_file",
            display_name="Write File",
            description="Write content to a file. Creates the file if it doesn't exist.",
            kind=ToolKind.WRITE,
            parameter_schema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to write"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file"
                    }
                },
                "required": ["file_path", "content"]
            }
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        file_path = params.get("file_path", "")
        content = params.get("content", "")
        
        try:
            # Create directories if needed
            dir_path = os.path.dirname(file_path)
            if dir_path:
                os.makedirs(dir_path, exist_ok=True)
            
            # Backup for undo
            old_content = None
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        old_content = f.read()
                except: pass
            
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Record for undo
            undo_stack = kwargs.get("undo_stack")
            if undo_stack:
                if old_content is not None:
                    undo_stack.push("delete", file_path, old_content) # Restore old
                else:
                    undo_stack.push("create", file_path) # Delete it

            return ToolResult(
                success=True,
                output=f"Successfully wrote {len(content)} characters to {file_path}",
                data={"file_path": file_path, "bytes_written": len(content)}
            )
        except Exception as e:
            return ToolResult(False, "", str(e))


class ShellTool(BaseTool):
    """Tool to execute shell commands (inspired by Gemini CLI's ShellTool)."""
    
    def __init__(self):
        super().__init__(
            name="shell",
            display_name="Shell",
            description="Execute a shell command. Returns stdout, stderr, and exit code.",
            kind=ToolKind.EXECUTE,
            parameter_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute"
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what this command does"
                    },
                    "working_dir": {
                        "type": "string",
                        "description": "Optional working directory for the command"
                    }
                },
                "required": ["command"]
            }
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        command = params.get("command", "")
        working_dir = params.get("working_dir", WORKSPACE_DIR)
        timeout = kwargs.get("timeout", 30)
        
        # Security check
        is_safe, reason = SecurityPolicy.check_command_safety(command)
        if not is_safe:
            return ToolResult(False, "", reason)
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"}
            )
            
            llm_content = f"""Command: {command}
Directory: {working_dir}
Output: {result.stdout or '(empty)'}
Error: {result.stderr or '(none)'}
Exit Code: {result.returncode}"""
            
            error_msg = result.stderr if result.returncode != 0 else None
            if error_msg:
                # Add hint for search commands
                if any(x in command.lower() for x in ["where ", "dir /s"]):
                    error_msg += "\n💡 PRO TIP: Use the 'find' action for a deeper system-wide search."
            
            return ToolResult(
                success=result.returncode == 0,
                output=result.stdout,
                error=error_msg,
                data={"exit_code": result.returncode},
                llm_content=llm_content,
                return_display=result.stdout or error_msg or f"Exit code: {result.returncode}"
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(False, "", f"Command timed out after {timeout} seconds")
        except Exception as e:
            return ToolResult(False, "", str(e))


class CreatePythonFileTool(BaseTool):
    """Tool to create and optionally execute Python files."""
    
    def __init__(self):
        super().__init__(
            name="create_python_file",
            display_name="Create Python File",
            description="Create a Python file with the given code and optionally execute it.",
            kind=ToolKind.WRITE,
            parameter_schema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to write to the file"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Optional filename (auto-generated if not provided)"
                    },
                    "execute": {
                        "type": "boolean",
                        "description": "Whether to execute the file after creating it"
                    }
                },
                "required": ["code"]
            }
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        code = params.get("code", "")
        filename = params.get("filename")
        should_execute = params.get("execute", True)
        
        # Clean code
        code = self._clean_code(code)
        
        # Security check
        is_safe, reason = SecurityPolicy.check_code_safety(code)
        if not is_safe:
            return ToolResult(False, "", reason)
        
        # Generate filename
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"generated_{timestamp}_{uuid.uuid4().hex[:6]}.py"
        
        filepath = os.path.join(WORKSPACE_DIR, filename)
        
        try:
            # Write file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(code)
            
            # Record for undo
            undo_stack = kwargs.get("undo_stack")
            if undo_stack:
                undo_stack.push("create", filepath)
            
            result_data = {
                "filepath": filepath,
                "filename": filename,
                "code_length": len(code)
            }
            
            # Execute if requested
            if should_execute:
                exec_result = subprocess.run(
                    [sys.executable, filepath],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=WORKSPACE_DIR,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"}
                )
                
                result_data["output"] = exec_result.stdout
                result_data["errors"] = exec_result.stderr
                result_data["exit_code"] = exec_result.returncode
                
                return ToolResult(
                    success=exec_result.returncode == 0,
                    output=exec_result.stdout,
                    error=exec_result.stderr if exec_result.returncode != 0 else None,
                    data=result_data,
                    llm_content=f"Created and executed: {filepath}\nOutput: {exec_result.stdout}\nErrors: {exec_result.stderr}",
                    return_display=exec_result.stdout or exec_result.stderr
                )
            
            return ToolResult(
                success=True,
                output=f"Created file: {filepath}",
                data=result_data
            )
            
        except subprocess.TimeoutExpired:
            return ToolResult(False, "", "Code execution timed out")
        except Exception as e:
            return ToolResult(False, "", str(e))
    
    def _clean_code(self, code: str) -> str:
        """Remove markdown code blocks and clean up the code."""
        code = re.sub(r"```python\s*\n?", "", code)
        code = re.sub(r"```\s*\n?", "", code)
        return code.strip()


class ListDirectoryTool(BaseTool):
    """Tool to list directory contents."""
    
    def __init__(self):
        super().__init__(
            name="list_directory",
            display_name="List Directory",
            description="List files and directories in a given path.",
            kind=ToolKind.READ,
            parameter_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Optional glob pattern to filter files"
                    }
                },
                "required": ["path"]
            }
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        import glob as glob_module
        
        path = params.get("path", ".")
        pattern = params.get("pattern", "*")
        
        try:
            if not os.path.exists(path):
                return ToolResult(False, "", f"Path not found: {path}")
            
            if os.path.isfile(path):
                return ToolResult(False, "", f"Path is a file, not a directory: {path}")
            
            full_pattern = os.path.join(path, pattern)
            items = glob_module.glob(full_pattern)
            
            result_items = []
            for item in items[:50]:  # Limit to 50 items
                stat = os.stat(item)
                result_items.append({
                    "name": os.path.basename(item),
                    "path": item,
                    "is_dir": os.path.isdir(item),
                    "size": stat.st_size
                })
            
            output = "\n".join([
                f"{'[DIR]' if i['is_dir'] else '[FILE]'} {i['name']}"
                for i in result_items
            ])
            
            return ToolResult(
                success=True,
                output=output,
                data={"items": result_items, "count": len(result_items)}
            )
            
        except Exception as e:
            return ToolResult(False, "", str(e))


class SearchFilesTool(BaseTool):
    """Tool to search for files by name or content."""
    
    def __init__(self):
        super().__init__(
            name="search_files",
            display_name="Search Files",
            description="Search for files by name pattern or content.",
            kind=ToolKind.SEARCH,
            parameter_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory to search in"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Filename pattern (glob style)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Optional content to search for within files"
                    }
                },
                "required": ["path", "pattern"]
            }
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        import glob as glob_module
        
        path = params.get("path", ".")
        pattern = params.get("pattern", "*")
        content_search = params.get("content")
        
        try:
            full_pattern = os.path.join(path, "**", pattern)
            files = glob_module.glob(full_pattern, recursive=True)
            
            results = []
            for f in files[:100]:  # Limit to 100 files
                if os.path.isfile(f):
                    if content_search:
                        try:
                            with open(f, "r", encoding="utf-8", errors="ignore") as file:
                                if content_search.lower() in file.read().lower():
                                    results.append(f)
                        except:
                            pass
                    else:
                        results.append(f)
            
            output = "\n".join(results[:50])
            
            return ToolResult(
                success=True,
                output=output,
                data={"files": results[:50], "count": len(results)}
            )
            
        except Exception as e:
            return ToolResult(False, "", str(e))

class DeleteFileTool(BaseTool):
    """Tool to delete a file or empty directory."""
    
    def __init__(self):
        super().__init__(
            name="delete_file",
            display_name="Delete File",
            description="Delete a file or an empty directory.",
            kind=ToolKind.WRITE,
            parameter_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file or directory to delete"
                    }
                },
                "required": ["path"]
            }
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        path = params.get("path")
        
        try:
            if not os.path.exists(path):
                return ToolResult(False, "", f"Path not found: {path}")
            
            # Basic security check - don't delete system files
            abs_path = os.path.abspath(path).lower()
            if any(x in abs_path for x in ["c:\\windows", "c:\\program files", "c:\\users\\vyas s\\desktop"]):
                 if not abs_path.startswith(WORKSPACE_DIR.lower()):
                     return ToolResult(False, "", "Safety Block: Deletion of system or desktop files is restricted.")

            # Backup for undo
            content = None
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            
            undo_stack = kwargs.get("undo_stack")
            
            if os.path.isfile(path):
                os.remove(path)
                if undo_stack: undo_stack.push("delete", path, content)
                return ToolResult(True, f"Successfully deleted file: {path}")
            else:
                os.rmdir(path)
                if undo_stack: undo_stack.push("delete", path, None)
                return ToolResult(True, f"Successfully deleted directory: {path}")
                
        except OSError as e:
            return ToolResult(False, "", f"Failed to delete {path}: {e}")
        except Exception as e:
            return ToolResult(False, "", str(e))


class CreateDirectoryTool(BaseTool):
    """Tool to create a new directory."""
    
    def __init__(self):
        super().__init__(
            name="create_directory",
            display_name="Create Directory",
            description="Create a new directory at the specified path.",
            kind=ToolKind.WRITE,
            parameter_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path of the directory to create"
                    }
                },
                "required": ["path"]
            }
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        path = params.get("path")
        
        try:
            os.makedirs(path, exist_ok=True)
            undo_stack = kwargs.get("undo_stack")
            if undo_stack: undo_stack.push("create", path)
            return ToolResult(True, f"Successfully created directory: {path}")
        except Exception as e:
            return ToolResult(False, "", str(e))


class FileSystemTreeTool(BaseTool):
    """Tool to show a tree-like structure of the file system."""
    
    def __init__(self):
        super().__init__(
            name="file_tree",
            display_name="File System Tree",
            description="Display a tree-like visual structure of files and directories.",
            kind=ToolKind.SEARCH,
            parameter_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Root path for the tree (default: workspace)"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum depth to traverse (default: 3)"
                    }
                }
            }
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        path = params.get("path", WORKSPACE_DIR)
        max_depth = int(params.get("max_depth", 3))
        
        if not os.path.exists(path):
            return ToolResult(False, "", f"Path not found: {path}")
            
        tree_str = f"📂 {os.path.abspath(path)}\n"
        tree_str += self._build_tree(path, "", 0, max_depth)
        
        return ToolResult(True, tree_str)
        
    def _build_tree(self, root: str, prefix: str, depth: int, max_depth: int) -> str:
        if depth >= max_depth:
            return ""
            
        try:
            items = os.listdir(root)
        except Exception:
            return ""
            
        # Filter hidden
        items = [i for i in items if not i.startswith('.')]
        items.sort(key=lambda x: (not os.path.isdir(os.path.join(root, x)), x.lower()))
        
        tree = ""
        for i, item in enumerate(items):
            is_last = (i == len(items) - 1)
            connector = "└── " if is_last else "├── "
            
            item_path = os.path.join(root, item)
            is_dir = os.path.isdir(item_path)
            
            icon = "📁 " if is_dir else "📄 "
            tree += f"{prefix}{connector}{icon}{item}\n"
            
            if is_dir:
                ext_prefix = prefix + ("    " if is_last else "│   ")
                tree += self._build_tree(item_path, ext_prefix, depth + 1, max_depth)
                
        return tree


                
        return tree


class TrieNode:
    """A node in the Trie (Prefix Tree) data structure."""
    def __init__(self):
        self.children: Dict[str, 'TrieNode'] = {}
        self.is_end_of_word = False
        self.full_path = ""

class FileTrieIndexerTool(BaseTool):
    """Tool to index files using a Trie data structure for fast prefix searching."""
    
    def __init__(self):
        super().__init__(
            name="fetch_file",
            display_name="Fetch File (Trie)",
            description="Fetch files near-instantly using a Trie (Prefix Tree) data structure by their prefix.",
            kind=ToolKind.SEARCH,
            parameter_schema={
                "type": "object",
                "properties": {
                    "prefix": {
                        "type": "string",
                        "description": "Prefix of the filename to search for"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["search", "index"],
                        "description": "Whether to search the index or rebuild it (default: search)"
                    }
                },
                "required": ["prefix"]
            }
        )
        self.root = TrieNode()
        self._indexed = False
        self.index_file = os.path.join(WORKSPACE_DIR, ".trie_index.json")
        self._load_index()

    def _insert(self, filename: str, full_path: str):
        node = self.root
        for char in filename:
            if char not in node.children:
                node.children[char] = TrieNode()
            node = node.children[char]
        node.is_end_of_word = True
        node.full_path = full_path

    def _build_index(self, directory: str):
        self.root = TrieNode() # Reset
        for root, _, files in os.walk(directory):
            # Skip hidden
            if any(part.startswith('.') for part in root.split(os.sep)):
                continue
            for file in files:
                if not file.startswith('.'):
                    self._insert(file, os.path.join(root, file))
        self._indexed = True

    def _search(self, prefix: str) -> List[str]:
        node = self.root
        for char in prefix:
            if char not in node.children:
                return []
            node = node.children[char]
        
        results = []
        self._collect_all(node, results)
        return results

    def _collect_all(self, node: TrieNode, results: List[str]):
        if node.is_end_of_word:
            results.append(node.full_path)
        for child in node.children.values():
            self._collect_all(child, results)

    def _save_index(self):
        """Serialize the Trie to a JSON file."""
        data = []
        self._serialize(self.root, "", data)
        try:
            with open(self.index_file, "w") as f:
                json.dump(data, f)
        except: pass

    def _serialize(self, node: TrieNode, path: str, data: List[Dict]):
        if node.is_end_of_word:
            data.append({"filename": path, "full_path": node.full_path})
        for char, child in node.children.items():
            self._serialize(child, path + char, data)

    def _load_index(self):
        """Load the Trie from a JSON file."""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, "r") as f:
                    data = json.load(f)
                    for item in data:
                        self._insert(item["filename"], item["full_path"])
                self._indexed = True
            except: pass

    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        action = params.get("action", "search")
        prefix = params.get("prefix", "")
        
        if action == "index" or not self._indexed:
            print(f"   🏗️ Building Trie index for {WORKSPACE_DIR}...")
            self._build_index(WORKSPACE_DIR)
            self._save_index()
            if action == "index":
                return ToolResult(True, f"Trie index built and persisted for {WORKSPACE_DIR}")

        matches = self._search(prefix)
        if matches:
            output = "\n".join(matches[:10])
            return ToolResult(True, f"Found {len(matches)} match(es) in Trie:\n{output}", {"matches": matches})
        else:
            return ToolResult(False, "", f"No files starting with '{prefix}' found in Trie index.")


class LockScreenTool(BaseTool):
    """Tool to lock the computer screen."""
    
    def __init__(self):
        super().__init__(
            name="lock_screen",
            display_name="Lock Screen",
            description="Lock the system screen immediately.",
            kind=ToolKind.READ,
            parameter_schema={"type": "object", "properties": {}}
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        try:
            import ctypes
            import platform
            if platform.system() == 'Windows':
                ctypes.windll.user32.LockWorkStation()
                return ToolResult(True, "Screen locked successfully.")
            else:
                return ToolResult(False, "", "Lock screen is only implemented for Windows.")
        except Exception as e:
            return ToolResult(False, "", str(e))


class DetailedStatusTool(BaseTool):
    """Tool to get detailed system resource status."""
    
    def __init__(self):
        super().__init__(
            name="detailed_status",
            display_name="Detailed Status",
            description="Get real-time CPU, Memory, Disk, and Battery statistics.",
            kind=ToolKind.READ,
            parameter_schema={"type": "object", "properties": {}}
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        try:
            import psutil
            import socket
            
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            battery = psutil.sensors_battery()
            
            stats = [
                f"💻 Device: {socket.gethostname()}",
                f"🔥 CPU: {cpu}%",
                f"🧠 RAM: {mem.percent}% ({round(mem.used/1024**3, 1)}GB / {round(mem.total/1024**3, 1)}GB)",
                f"📁 Disk: {disk.percent}% ({round(disk.free/1024**3, 1)}GB free)",
            ]
            
            if battery:
                stats.append(f"🔋 Battery: {battery.percent}% ({'Plugged in' if battery.power_plugged else 'Discharging'})")
                
            return ToolResult(True, "\n".join(stats), {"cpu": cpu, "memory": mem.percent, "disk": disk.percent})
        except ImportError:
            return ToolResult(False, "", "Psutil library not found. Resource stats unavailable.")
        except Exception as e:
            return ToolResult(False, "", str(e))


class ProcessManagerTool(BaseTool):
    """Tool to manage system processes."""
    
    def __init__(self):
        super().__init__(
            name="process_manager",
            display_name="Process Manager",
            description="List top processes or kill a specific process by PID or name.",
            kind=ToolKind.WRITE,
            parameter_schema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["list", "kill"],
                        "description": "Action to perform (default: list)"
                    },
                    "target": {
                        "type": "string",
                        "description": "PID or name of the process to kill"
                    }
                }
            }
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        action = params.get("action", "list")
        target = params.get("target")
        
        try:
            import psutil
            
            if action == "list":
                procs = []
                for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                    try:
                        pinfo = proc.info
                        if pinfo['memory_percent'] > 0.5: # Only show heavy ones
                            procs.append(pinfo)
                    except: pass
                
                procs = sorted(procs, key=lambda x: x['memory_percent'], reverse=True)[:10]
                output = "Top Processes:\n" + "\n".join([f"[{p['pid']}] {p['name']} ({round(p['memory_percent'], 1)}%)" for p in procs])
                return ToolResult(True, output)
            
            elif action == "kill":
                if not target: return ToolResult(False, "", "Target PID or name required to kill.")
                
                count = 0
                for proc in psutil.process_iter():
                    try:
                        if str(proc.pid) == target or proc.name().lower() == target.lower():
                            proc.kill()
                            count += 1
                    except: pass
                
                if count > 0:
                    return ToolResult(True, f"Killed {count} process(es) matching '{target}'.")
                else:
                    return ToolResult(False, "", f"No process found matching '{target}'.")
                    
        except ImportError:
            return ToolResult(False, "", "Psutil library required.")
        except Exception as e:
            return ToolResult(False, "", str(e))


class VolumeControlTool(BaseTool):
    """Tool to control system volume."""
    
    def __init__(self):
        super().__init__(
            name="volume_control",
            display_name="Volume Control",
            description="Adjust system volume level (0-100).",
            kind=ToolKind.WRITE,
            parameter_schema={
                "type": "object",
                "properties": {
                    "level": {
                        "type": "integer",
                        "description": "Volume level (0-100)"
                    }
                },
                "required": ["level"]
            }
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        level = params.get("level", 50)
        try:
            import platform
            if platform.system() == 'Windows':
                # Use powershell for volume
                ps_cmd = f"$obj = New-Object -ComObject WScript.Shell; 1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}; 1..{level//2} | ForEach-Object {{ $obj.SendKeys([char]175) }}"
                subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True)
                return ToolResult(True, f"System volume set to ~{level}%.")
            else:
                return ToolResult(False, "", "Volume control via shell is Windows-only for now.")
        except Exception as e:
            return ToolResult(False, "", str(e))


class SystemSettingsTool(BaseTool):
    """Tool to open system settings (Windows)."""
    
    def __init__(self):
        super().__init__(
            name="system_settings",
            display_name="System Settings",
            description="Open various system settings pages (Windows).",
            kind=ToolKind.READ,
            parameter_schema={
                "type": "object",
                "properties": {
                    "page": {
                        "type": "string",
                        "description": "Settings page (e.g., windowsupdate, display, sound, network, apps)"
                    }
                },
                "required": ["page"]
            }
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        page = params.get("page", "").lower()
        
        settings_map = {
            "update": "ms-settings:windowsupdate",
            "windowsupdate": "ms-settings:windowsupdate",
            "display": "ms-settings:display",
            "sound": "ms-settings:sound",
            "network": "ms-settings:network",
            "wifi": "ms-settings:network-wifi",
            "bluetooth": "ms-settings:bluetooth",
            "apps": "ms-settings:appsfeatures",
            "battery": "ms-settings:batterysaver",
            "storage": "ms-settings:storagesense",
            "personalization": "ms-settings:personalization",
            "accounts": "ms-settings:yourinfo",
            "time": "ms-settings:dateandtime",
            "privacy": "ms-settings:privacy"
        }
        
        uri = settings_map.get(page, "ms-settings:" + page)
        
        try:
            import platform
            if platform.system() == "Windows":
                subprocess.Popen(f'start {uri}', shell=True)
                return ToolResult(True, f"Opening settings page: {page}")
            else:
                return ToolResult(False, "", "System settings control is only available on Windows.")
        except Exception as e:
            return ToolResult(False, "", str(e))


class UndoStackTool(BaseTool):
    """Tool to undo the last file operation using a Stack (LIFO)."""
    
    def __init__(self):
        super().__init__(
            name="undo",
            display_name="Undo Operation",
            description="Undo the last file creation or deletion.",
            kind=ToolKind.WRITE,
            parameter_schema={"type": "object", "properties": {}}
        )
        self.stack = [] # Stack of (type, path, optional_content)

    def push(self, op_type: str, path: str, content: str = None):
        self.stack.append((op_type, path, content))

    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        if not self.stack:
            return ToolResult(False, "", "Nothing to undo.")
        
        op_type, path, content = self.stack.pop()
        
        try:
            if op_type == "create":
                # Undo creation by deleting
                if os.path.exists(path):
                    if os.path.isfile(path): os.remove(path)
                    else: os.rmdir(path)
                    return ToolResult(True, f"Undid creation: Removed {path}")
            elif op_type == "delete":
                # Undo deletion by recreating
                if content is not None:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)
                    return ToolResult(True, f"Undid deletion: Restored {path}")
                else:
                    os.makedirs(path, exist_ok=True)
                    return ToolResult(True, f"Undid deletion: Restored directory {path}")
        except Exception as e:
            return ToolResult(False, "", f"Undo failed: {e}")
        
        return ToolResult(False, "", "Undo operation type mismatch.")


class WorkspaceGraphTool(BaseTool):
    """Tool to map workspace as a dependency graph (Adjacency List)."""
    
    def __init__(self):
        super().__init__(
            name="map_workspace",
            display_name="Workspace Mapper",
            description="Generate a dependency graph of imports in the workspace.",
            kind=ToolKind.READ,
            parameter_schema={"type": "object", "properties": {}}
        )

    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        graph = {} # Adjacency list: file -> [dependencies]
        
        for root, _, files in os.walk(WORKSPACE_DIR):
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    rel_path = os.path.relpath(path, WORKSPACE_DIR)
                    deps = self._parse_imports(path)
                    graph[rel_path] = deps
        
        output = "📦 Workspace Dependency Graph:\n"
        for node, edges in graph.items():
            if edges:
                output += f"  {node} ➔ {', '.join(edges)}\n"
            else:
                output += f"  {node} (No local dependencies)\n"
        
        return ToolResult(True, output, graph)

    def _parse_imports(self, filepath: str) -> List[str]:
        deps = []
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Simple regex for local imports
                import_matches = re.findall(r"^(?:from|import)\s+([\w\.]+)", content, re.MULTILINE)
                for imp in import_matches:
                    # Filter for likely local modules (heuristic)
                    if "." in imp or os.path.exists(os.path.join(WORKSPACE_DIR, imp + ".py")):
                        deps.append(imp)
        except: pass
        return list(set(deps))


class FileExplorerSettingTool(BaseTool):
    """Tool to configure File Explorer settings via Windows Registry."""
    
    def __init__(self):
        super().__init__(
            name="explorer_settings",
            display_name="Explorer Settings",
            description="Toggle File Explorer preferences like hidden files or extensions.",
            kind=ToolKind.WRITE,
            parameter_schema={
                "type": "object",
                "properties": {
                    "setting": {
                        "type": "string",
                        "enum": ["hidden", "extensions"],
                        "description": "Setting to toggle"
                    },
                    "enabled": {
                        "type": "boolean",
                        "description": "Whether to enable (True) or disable (False)"
                    }
                },
                "required": ["setting", "enabled"]
            }
        )

    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        setting = params.get("setting")
        enabled = 1 if params.get("enabled", True) else 0
        
        try:
            import winreg
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
            reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
            
            if setting == "hidden":
                winreg.SetValueEx(reg_key, "Hidden", 0, winreg.REG_DWORD, 1 if enabled else 2) # 1=Show, 2=Hide
            elif setting == "extensions":
                winreg.SetValueEx(reg_key, "HideFileExt", 0, winreg.REG_DWORD, 0 if enabled else 1) # 0=Show, 1=Hide
            
            winreg.CloseKey(reg_key)
            
            # Refresh explorer
            subprocess.run("taskkill /f /im explorer.exe && start explorer.exe", shell=True)
            return ToolResult(True, f"Successfully updated Explorer setting '{setting}' to {'enabled' if enabled else 'disabled'}. Explorer restarted.")
            
        except ImportError:
            return ToolResult(False, "", "Winreg is Windows-only.")
        except Exception as e:
            return ToolResult(False, "", str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# TOOL REGISTRY (Inspired by Gemini CLI's ToolRegistry)
# ═══════════════════════════════════════════════════════════════════════════════

class FindEverywhereTool(BaseTool):
    """Tool to search for a file across the entire computer."""
    
    def __init__(self):
        super().__init__(
            name="find_everywhere",
            display_name="Find Everywhere",
            description="Search for a file by name starting from root on all available drives.",
            kind=ToolKind.SEARCH,
            parameter_schema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The exact name or pattern of the file to find"
                    }
                },
                "required": ["filename"]
            }
        )
    
    def execute(self, params: Dict[str, Any], **kwargs) -> ToolResult:
        import string
        import subprocess
        filename = params.get("filename", "")
        results = []
        
        # Determine drives on Windows
        drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        
        print(f"   🔍 Searching for '{filename}' across drives: {', '.join(drives)}")
        
        for drive in drives:
            try:
                # Use 'where' command if searching for an executable, or 'dir /s /b'
                # dir /s /b /a is quite fast for filename-only search
                cmd = f'dir {drive}{filename} /s /b'
                proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
                if proc.stdout:
                    results.extend(proc.stdout.strip().split("\n"))
            except Exception:
                continue
            
            if len(results) >= 10: break # Don't overwhelm
            
        if results:
            output = "\n".join(results[:10])
            return ToolResult(True, output, data={"matches": results})
        else:
            return ToolResult(False, "", f"File '{filename}' not found anywhere on the system.")

class ToolRegistry:
    """Registry for managing available tools."""
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._undo_tool = UndoStackTool()
        self._register_builtin_tools()
        self.register(self._undo_tool)
    
    def _register_builtin_tools(self):
        """Register all built-in tools."""
        builtin_tools = [
            ReadFileTool(),
            WriteFileTool(),
            ShellTool(),
            CreatePythonFileTool(),
            ListDirectoryTool(),
            SearchFilesTool(),
            FindEverywhereTool(),
            DeleteFileTool(),
            CreateDirectoryTool(),
            FileSystemTreeTool(),
            SystemSettingsTool(),
            FileTrieIndexerTool(),
            LockScreenTool(),
            DetailedStatusTool(),
            ProcessManagerTool(),
            VolumeControlTool(),
            WorkspaceGraphTool(),
            FileExplorerSettingTool(),
        ]
        for tool in builtin_tools:
            self.register(tool)
    
    def register(self, tool: BaseTool):
        """Register a tool."""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def get_all(self) -> List[BaseTool]:
        """Get all registered tools."""
        return list(self._tools.values())
    
    def get_function_declarations(self) -> List[Dict]:
        """Get function declarations for LLM."""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameter_schema
            }
            for tool in self._tools.values()
        ]
    
    def execute(self, tool_name: str, params: Dict[str, Any], **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(False, "", f"Unknown tool: {tool_name}")
        
        validation_error = tool.validate_params(params)
        if validation_error:
            return ToolResult(False, "", validation_error)
        
        return tool.execute(params, undo_stack=self._undo_tool, **kwargs)


# ═══════════════════════════════════════════════════════════════════════════════
# OLLAMA CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class OllamaClient:
    """Client for Ollama API."""
    
    def __init__(self, base_url: str = OLLAMA_URL):
        self.base_url = base_url
    
    def chat(self, model: str, messages: List[Dict], tools: List[Dict] = None) -> Dict:
        """Send a chat request to Ollama."""
        import urllib.request
        
        url = f"{self.base_url}/api/chat"
        data = {
            "model": model,
            "messages": messages,
            "stream": False
        }
        
        if tools:
            data["tools"] = tools
        
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode())
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
# ENHANCED MCP AGENT (Main AI Agent Class)
# ═══════════════════════════════════════════════════════════════════════════════

class EnhancedMCPAgent:
    """
    Enhanced MCP Agent inspired by Gemini CLI architecture.
    
    Features:
    - Tool registry with multiple built-in tools
    - Security policy enforcement
    - Code generation and execution
    - Conversation history
    """
    
    SYSTEM_PROMPT = """You are NOVA, a powerful AI assistant that can generate code AND perform actions like controlling your laptop.

## MODE 1: CODE GENERATION
When asked to create/write a program, output ONLY the Python code:
- No explanations before or after
- Include all imports
- Make code standalone and executable

Example:
User: Create a program that prints hello world
Response:
print("Hello World")

## MODE 2: ACTION COMMANDS
When asked to perform actions (git, system control, etc.), output commands in this format:
[ACTION:type] command

Available action types:
- [ACTION:shell] Run a shell command
- [ACTION:git] Git operations (add, commit, push)
- [ACTION:open] Open an application
- [ACTION:file] File operations
- [ACTION:find] Find a file everywhere on the computer

## CRITICAL: FILE SEARCHING
If the user asks to "find", "search", or "where is" a file, you MUST use [ACTION:find]. Do NOT use [ACTION:shell] with 'where' or 'dir' for searching files, as they are not deep enough.

## MODE 3: ADAPT & FIND
If a command fails because a file or tool (like gh.exe) is missing, you MUST use the [ACTION:find] tool to search the entire computer for it.

Example:
User: Push to github
(Git fails because gh.exe is not found at a specific path)
Response:
[ACTION:find] gh.exe

Examples:
User: Push to github
Response:
[ACTION:git] push

User: Open chrome
Response:
[ACTION:open] chrome

User: List all files
Response:
[ACTION:shell] dir

## IMPORTANT:
- For code generation: output ONLY Python code
- For actions: use [ACTION:type] format
- Never mix code with action commands"""

    def __init__(self, model: str = DEFAULT_MODEL):
        self.model = model
        self.client = OllamaClient()
        self.registry = ToolRegistry()
        self.history: List[Dict] = []
        self.conversation_history: List[Dict] = []
    
    def get_tools_description(self) -> str:
        """Get formatted tools description."""
        tools = self.registry.get_all()
        descriptions = []
        for tool in tools:
            descriptions.append(f"- {tool.name}: {tool.description}")
        return "\n".join(descriptions)
    
    def run(self, prompt: str, auto_execute: bool = True) -> Dict[str, Any]:
        """
        Run the agent with a user prompt.
        """
        result = {
            "prompt": prompt,
            "success": False,
            "code": None,
            "output": None,
            "errors": None,
            "tool_calls": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # DIRECT COMMAND DETECTION - Handle actions without LLM
        direct_action = self._detect_direct_action(prompt)
        if direct_action:
            action_type = direct_action["type"]
            action_cmd = direct_action["command"]
            
            print(f"\n⚠️  Action detected: [{action_type.upper()}] {action_cmd}")
            confirm = input("   Execute this action? (y/n): ").strip().lower()
            
            if confirm == 'y':
                action_result = self._execute_action(action_type, action_cmd)
                result["output"] = action_result.get("output", "")
                result["errors"] = action_result.get("error")
                result["success"] = action_result.get("success", False)
            else:
                print("   ❌ Action cancelled")
                sys.stdout.flush()
                result["output"] = "Action cancelled by user"
                result["success"] = True
            
            return result
        
        # Check Ollama
        if not self.client.is_available():
            result["errors"] = "Ollama is not running. Start it with 'ollama serve'"
            return result
        
        # Build system prompt
        system_prompt = self.SYSTEM_PROMPT
        
        # Build messages
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for msg in self.conversation_history[-10:]:
            messages.append(msg)
        
        messages.append({"role": "user", "content": prompt})
        
        if RICH_AVAILABLE and console:
            console.print("\n[bold bright_cyan]🧠 Processing with AI...[/]")
        else:
            print("\n🧠 Processing with AI...")
        
        # Call LLM
        response = self.client.chat(self.model, messages)
        
        if "error" in response:
            result["errors"] = f"LLM Error: {response['error']}"
            return result
        
        llm_output = response.get("message", {}).get("content", "")
        
        # Save to conversation history
        self.conversation_history.append({"role": "user", "content": prompt})
        self.conversation_history.append({"role": "assistant", "content": llm_output})
        
        # Parse and execute tool calls
        tool_calls = self._parse_tool_calls(llm_output)
        
        if tool_calls:
            if RICH_AVAILABLE and console:
                console.print(f"[bold cyan]🔧 Executing {len(tool_calls)} tool call(s)...[/]")
            else:
                print(f"🔧 Executing {len(tool_calls)} tool call(s)...")
            
            for tool_call in tool_calls:
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("arguments", {})
                
                print(f"   → {tool_name}({json.dumps(tool_args)[:50]}...)")
                
                tool_result = self.registry.execute(tool_name, tool_args)
                
                result["tool_calls"].append({
                    "tool": tool_name,
                    "arguments": tool_args,
                    "result": {
                        "success": tool_result.success,
                        "output": tool_result.output,
                        "error": tool_result.error
                    }
                })
                
                if tool_result.success:
                    result["output"] = (result.get("output") or "") + tool_result.output
                else:
                    result["errors"] = (result.get("errors") or "") + (tool_result.error or "")
            
            result["success"] = all(tc["result"]["success"] for tc in result["tool_calls"])
        else:
            # Check for action commands first
            actions = self._parse_actions(llm_output)
            
            if actions:
                if RICH_AVAILABLE and console:
                    console.print(f"[bold yellow]🎯 Found {len(actions)} action(s) to execute...[/]")
                else:
                    print(f"🎯 Found {len(actions)} action(s) to execute...")
                
                for action in actions:
                    action_type = action.get("type")
                    action_cmd = action.get("command")
                    
                    # Ask for permission
                    print(f"\n⚠️  Action requested: [{action_type.upper()}] {action_cmd}")
                    confirm = input("   Execute this action? (y/n): ").strip().lower()
                    
                    if confirm == 'y':
                        action_result = self._execute_action(action_type, action_cmd)
                        result["output"] = (result.get("output") or "") + action_result.get("output", "")
                        if action_result.get("error"):
                            result["errors"] = (result.get("errors") or "") + action_result["error"]
                        result["success"] = action_result.get("success", False)
                    else:
                        print("   ❌ Action cancelled by user")
                        result["output"] = "Action cancelled by user"
                        result["success"] = True
            
            # Check if it's code that should be executed
            elif self._extract_code(llm_output):
                code = self._extract_code(llm_output)
                print("📄 Detected Python code, creating and executing...")
                
                result["code"] = code
                tool_result = self.registry.execute("create_python_file", {
                    "code": code,
                    "execute": True
                })
                
                result["success"] = tool_result.success
                result["output"] = tool_result.output
                result["errors"] = tool_result.error
                result["data"] = tool_result.data
            else:
                # Just a conversational response
                result["success"] = True
                result["output"] = llm_output
        
        # Save to history
        self.history.append(result)
        
        return result
    
    def _parse_tool_calls(self, response: str) -> List[Dict]:
        """Parse tool calls from LLM response."""
        tool_calls = []
        
        # Pattern 1: [TOOL:name] args
        tool_pattern = r'\[TOOL:(\w+)\]\s*(.+?)(?=\[TOOL:|$)'
        matches = re.findall(tool_pattern, response, re.DOTALL)
        
        for tool_name, args in matches:
            try:
                # Try to parse as JSON
                parsed_args = json.loads(args.strip())
            except:
                # Fall back to simple string arg
                parsed_args = {"input": args.strip()}
            
            tool_calls.append({"tool": tool_name, "arguments": parsed_args})
        
        # Pattern 2: JSON tool calls
        json_pattern = r'\{[^{}]*"tool"\s*:\s*"[^"]+"\s*,\s*"arguments"\s*:\s*\{[^{}]*\}[^{}]*\}'
        json_matches = re.findall(json_pattern, response)
        
        for json_str in json_matches:
            try:
                tool_call = json.loads(json_str)
                if "tool" in tool_call:
                    tool_calls.append(tool_call)
            except:
                pass
        
        return tool_calls
    
    def _extract_code(self, response: str) -> Optional[str]:
        """Extract Python code from response."""
        # Check for code blocks
        code_block_pattern = r"```python\s*\n([\s\S]*?)\n```"
        matches = re.findall(code_block_pattern, response)
        
        if matches:
            return matches[0].strip()
        
        # Check if the entire response looks like Python code
        lines = response.strip().split("\n")
        if lines and (
            lines[0].startswith("import ") or
            lines[0].startswith("from ") or
            lines[0].startswith("def ") or
            lines[0].startswith("class ") or
            lines[0].startswith("#")
        ):
            return response.strip()
        
        return None
    
    def _detect_direct_action(self, prompt: str) -> Optional[Dict[str, str]]:
        """Detect action commands directly from user prompt."""
        p = prompt.lower().strip()
        
        # Clean the prompt of common prefixes like 'agent> '
        prefixes = ["agent>", "nova>", "agent:", "nova:", "agent >", "nova >", "agent :", "nova :"]
        changed = True
        while changed:
            changed = False
            for prefix in prefixes:
                if p.startswith(prefix):
                    p = p[len(prefix):].strip()
                    changed = True
                    break
        
        # Git operations
        if p.startswith("git "):
            return {"type": "git", "command": p[4:].strip()}
        if any(cmd in p for cmd in ["push to github", "git push", "push my code"]):
            return {"type": "git", "command": "push"}
        
        # Open operations
        open_prefixes = ["open ", "start ", "launch ", "run "]
        for prefix in open_prefixes:
            if p.startswith(prefix):
                return {"type": "open", "command": p[len(prefix):].strip()}
        
        # Specific app triggers
        apps = ["chrome", "notepad", "calc", "explorer", "cmd", "powershell", "settings"]
        if p in apps:
            return {"type": "open", "command": p}
            
        # Find operations
        if p.startswith("find "):
            return {"type": "find", "command": p[5:].strip()}
        if p.startswith("search "):
            return {"type": "find", "command": p[7:].strip()}
        if p.startswith("where is "):
            return {"type": "find", "command": p[9:].strip()}

        # File system operations
        if p.startswith("mkdir ") or p.startswith("make dir "):
            return {"type": "file", "command": f"mkdir {p.split(' ', 1)[1].strip()}"}
        if p.startswith("delete ") or p.startswith("remove ") or p.startswith("rm "):
            return {"type": "file", "command": f"delete {p.split(' ', 1)[1].strip()}"}
        if p.startswith("tree"):
            cmd = p.split(" ", 1)[1].strip() if " " in p else "."
            return {"type": "file", "command": f"tree {cmd}"}
            
        # Advanced CS / System operations
        if p.startswith("fetch "):
            return {"type": "fetch", "command": p[6:].strip()}
        if p.startswith("index"):
            return {"type": "fetch", "command": "index"}
        if p == "lock" or p == "lock screen":
            return {"type": "lock", "command": ""}
        if p == "processes" or p == "top apps":
            return {"type": "processes", "command": "list"}
        if p.startswith("kill "):
            return {"type": "processes", "command": f"kill {p[5:].strip()}"}
        if p == "status" or p == "system status":
            return {"type": "status", "command": ""}
        if p.startswith("volume "):
            return {"type": "volume", "command": p[7:].strip()}
        if p == "undo":
            return {"type": "undo", "command": ""}
        if p == "map workspace" or p == "map" or p == "graph":
            return {"type": "map_workspace", "command": ""}
        if p.startswith("show hidden"):
            return {"type": "explorer_settings", "command": "hidden true"}
        if p.startswith("hide hidden"):
            return {"type": "explorer_settings", "command": "hidden false"}
        if p.startswith("show extensions"):
            return {"type": "explorer_settings", "command": "extensions true"}
        if p.startswith("hide extensions"):
            return {"type": "explorer_settings", "command": "extensions false"}

        return None

    def _parse_actions(self, response: str) -> List[Dict]:
        """Parse action commands from LLM response."""
        actions = []
        
        # Pattern: [ACTION:type] command
        action_pattern = r'\[ACTION:(\w+)\]\s*(.+?)(?=\[ACTION:|$)'
        matches = re.findall(action_pattern, response, re.DOTALL | re.IGNORECASE)
        
        for action_type, command in matches:
            actions.append({
                "type": action_type.lower().strip(),
                "command": command.strip()
            })
        
        return actions
    
    def _execute_action(self, action_type: str, command: str) -> Dict[str, Any]:
        """Execute an action command."""
        result = {"success": False, "output": "", "error": None}
        
        try:
            if action_type == "shell":
                # Execute shell command
                print(f"   🐚 Executing shell: {command}")
                proc = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=WORKSPACE_DIR
                )
                result["output"] = proc.stdout or proc.stderr or "Command executed"
                result["success"] = proc.returncode == 0
                if proc.returncode != 0:
                    result["error"] = proc.stderr
            
            elif action_type == "git":
                # Git operations
                print(f"   📤 Executing git: {command}")
                if command.lower() == "push":
                    proc = subprocess.run(
                        "git push",
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                elif command.lower() == "add":
                    proc = subprocess.run(
                        "git add .",
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                elif command.lower().startswith("commit"):
                    msg = command.replace("commit", "").strip() or "Update from NOVA"
                    proc = subprocess.run(
                        f'git commit -m "{msg}"',
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                else:
                    proc = subprocess.run(
                        f"git {command}",
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=60
                    )
                result["output"] = proc.stdout or proc.stderr or "Git command executed"
                result["success"] = proc.returncode == 0
                if proc.returncode != 0:
                    result["error"] = proc.stderr
            
            elif action_type == "open":
                # Open application
                print(f"   🚀 Opening: {command}")
                import platform
                if platform.system() == "Windows":
                    subprocess.Popen(f'start "" "{command}"', shell=True)
                elif platform.system() == "Darwin":
                    subprocess.Popen(f'open "{command}"', shell=True)
                else:
                    subprocess.Popen(f'xdg-open "{command}"', shell=True)
                result["output"] = f"Opened: {command}"
                result["success"] = True
            
            elif action_type == "file":
                # File operations
                print(f"   📁 File operation: {command}")
                parts = command.split(" ", 1)
                cmd = parts[0].lower()
                target = parts[1] if len(parts) > 1 else ""
                
                if cmd == "mkdir":
                    tool_result = self.registry.execute("create_directory", {"path": target})
                    result["output"] = tool_result.output
                    result["success"] = tool_result.success
                elif cmd == "delete":
                    tool_result = self.registry.execute("delete_file", {"path": target})
                    result["output"] = tool_result.output
                    result["success"] = tool_result.success
                elif cmd == "tree":
                    tool_result = self.registry.execute("file_tree", {"path": target or WORKSPACE_DIR})
                    result["output"] = tool_result.output
                    result["success"] = tool_result.success
                else:
                    result["output"] = f"File operation: {command}"
                    result["success"] = True
            
            elif action_type == "find":
                # Find a file everywhere
                print(f"   🌐 Adapting: Searching computer for {command}")
                tool_result = self.registry.execute("find_everywhere", {"filename": command})
                result["output"] = tool_result.output
                result["success"] = tool_result.success
                result["error"] = tool_result.error

            elif action_type == "fetch":
                # Trie based fetching
                print(f"   🌳 Trie Fetching: {command}")
                action = "index" if command == "index" else "search"
                tool_result = self.registry.execute("fetch_file", {"prefix": command, "action": action})
                result["output"] = tool_result.output
                result["success"] = tool_result.success
                result["error"] = tool_result.error

            elif action_type == "lock":
                # Lock screen
                print("   🔒 Locking screen...")
                tool_result = self.registry.execute("lock_screen", {})
                result["output"] = tool_result.output
                result["success"] = tool_result.success

            elif action_type == "processes":
                # Manage processes
                print(f"   ⚙️ Process Manager: {command}")
                action = "kill" if command.startswith("kill ") else "list"
                target = command.replace("kill ", "").strip() if action == "kill" else None
                tool_result = self.registry.execute("process_manager", {"action": action, "target": target})
                result["output"] = tool_result.output
                result["success"] = tool_result.success

            elif action_type == "status":
                # Detailed system status
                print("   📊 Gathering detailed system status...")
                tool_result = self.registry.execute("detailed_status", {})
                result["output"] = tool_result.output
                result["success"] = tool_result.success

            elif action_type == "volume":
                # Volume control
                print(f"   🔊 Setting volume: {command}")
                try:
                    level = int(command)
                    tool_result = self.registry.execute("volume_control", {"level": level})
                    result["output"] = tool_result.output
                    result["success"] = tool_result.success
                except:
                    result["error"] = "Invalid volume level. Please use 0-100."
            
            elif action_type == "undo":
                # Undo operation
                print("   ↩️ Undoing last operation...")
                tool_result = self.registry.execute("undo", {})
                result["output"] = tool_result.output
                result["success"] = tool_result.success

            elif action_type == "map_workspace":
                # Map workspace dependency graph
                print("   🕸️ Mapping workspace dependencies...")
                tool_result = self.registry.execute("map_workspace", {})
                result["output"] = tool_result.output
                result["success"] = tool_result.success

            elif action_type == "explorer_settings":
                # Configure explorer settings
                print(f"   📂 Updating Explorer setting: {command}")
                parts = command.split(" ", 1)
                setting = parts[0]
                enabled = "true" in parts[1].lower() if len(parts) > 1 else True
                tool_result = self.registry.execute("explorer_settings", {"setting": setting, "enabled": enabled})
                result["output"] = tool_result.output
                result["success"] = tool_result.success

            else:
                result["error"] = f"Unknown action type: {action_type}"
                
        except subprocess.TimeoutExpired:
            result["error"] = "Command timed out"
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def run_interactive(self):
        """Run the agent in interactive mode."""
        print("\n" + "=" * 60)
        print("   🚀 NOVA Enhanced MCP Agent")
        print("   Inspired by Gemini CLI Architecture")
        print("=" * 60)
        print(f"\nModel: {self.model}")
        print(f"Workspace: {WORKSPACE_DIR}")
        print(f"Available tools: {len(self.registry.get_all())}")
        print("\nType your prompt and press Enter.")
        print("Commands: /tools, /history, /clear, /exit")
        print("=" * 60 + "\n")
        
        while True:
            try:
                prompt = input("🧠 > ").strip()
                
                if not prompt:
                    continue
                
                if prompt.lower() in ["exit", "/exit", "quit", "/quit"]:
                    print("\n👋 Goodbye!")
                    break
                
                if prompt == "/tools":
                    print("\n📦 Available Tools:")
                    for tool in self.registry.get_all():
                        print(f"  - {tool.name}: {tool.description[:60]}...")
                    print()
                    continue
                
                if prompt == "/history":
                    print(f"\n📜 History ({len(self.history)} items)")
                    for i, h in enumerate(self.history[-5:], 1):
                        status = "✓" if h["success"] else "✗"
                        print(f"  {i}. [{status}] {h['prompt'][:40]}...")
                    print()
                    continue
                
                if prompt == "/clear":
                    self.history = []
                    self.conversation_history = []
                    print("✓ History cleared\n")
                    continue
                
                # Run the agent
                result = self.run(prompt)
                
                print("\n" + "-" * 50)
                
                if result.get("code"):
                    print("📄 Generated Code:")
                    code_lines = result["code"].split("\n")
                    for line in code_lines[:20]:
                        print(f"  {line}")
                    if len(code_lines) > 20:
                        print(f"  ... ({len(code_lines) - 20} more lines)")
                
                if result.get("output"):
                    print("\n▶ Output:")
                    print(result["output"][:1000])
                
                if result.get("errors"):
                    print(f"\n❌ Errors: {result['errors']}")
                
                if result.get("tool_calls"):
                    print(f"\n🔧 Tool calls: {len(result['tool_calls'])}")
                    for tc in result["tool_calls"]:
                        status = "✓" if tc["result"]["success"] else "✗"
                        print(f"  [{status}] {tc['tool']}")
                
                print("-" * 50 + "\n")
                
            except KeyboardInterrupt:
                print("\n")
            except Exception as e:
                print(f"\n❌ Error: {e}\n")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="NOVA Enhanced MCP Agent")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help="Ollama model to use")
    parser.add_argument("--prompt", "-p", help="Single prompt to run")
    args = parser.parse_args()
    
    agent = EnhancedMCPAgent(model=args.model)
    
    if args.prompt:
        result = agent.run(args.prompt)
        print(json.dumps(result, indent=2, default=str))
    else:
        agent.run_interactive()


if __name__ == "__main__":
    main()
