#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA - Advanced AI Coding Assistant
Version 1.0
"""

# Suppress ALL warnings and logging FIRST before any imports
import os
import sys
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '3'
os.environ['ABSL_MIN_LOG_LEVEL'] = '3'

import warnings
warnings.filterwarnings("ignore")

# Suppress absl logging
import logging
logging.disable(logging.WARNING)

import io
import json
import subprocess
import platform
import tempfile
import shutil
import socket
import threading
import webbrowser
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# Bluetooth support
try:
    from nova_bluetooth import BluetoothServer, list_com_ports
    BLUETOOTH_AVAILABLE = True
except ImportError:
    BLUETOOTH_AVAILABLE = False

# MCP Agent support (Enhanced - inspired by Gemini CLI)
try:
    from agent.enhanced_agent import EnhancedMCPAgent as MCPAgent
    AGENT_AVAILABLE = True
except ImportError:
    try:
        from agent.agent import MCPAgent
        AGENT_AVAILABLE = True
    except ImportError:
        AGENT_AVAILABLE = False

# Force UTF-8 encoding on Windows
if sys.platform == 'win32':
    # Set console to UTF-8
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)
    except:
        pass
    # Also wrap stdout/stderr
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Rich terminal UI
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.syntax import Syntax
    from rich.prompt import Prompt
    from rich.align import Align
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Gemini API
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Hugging Face
try:
    from huggingface_hub import InferenceClient
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

# System monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Neural Intent Engine (NIE) - Custom Local Brain
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    WORKSPACE_DIR = os.path.join(SCRIPT_DIR, "workspace")
    if WORKSPACE_DIR not in sys.path:
        sys.path.append(WORKSPACE_DIR)
    
    from intent_engine import NeuralIntentEngine
    from engine_interface.permission_gate import PermissionGate
    NIE_AVAILABLE = True
except Exception as e:
    NIE_AVAILABLE = False

# Windows-specific
try:
    import ctypes
    from ctypes import wintypes
    CTYPES_AVAILABLE = True
except ImportError:
    CTYPES_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

NOVA_VERSION = "1.1 (New)"
DEVICE_NAME = socket.gethostname()  # Auto-detect device name
WEB_PORT = 8080
OLLAMA_URL = "http://localhost:11434"  # Ollama default

# Available Models (Ollama only)
MODELS = {
    "1": {
        "key": "nova",
        "name": "nova",
        "provider": "ollama",
        "description": "NOVA - Custom model with tool execution (LOCAL)"
    },
    "2": {
        "key": "llama3",
        "name": "llama3.2",
        "provider": "ollama",
        "description": "Llama 3.2 - Fast & capable (LOCAL)"
    },
    "3": {
        "key": "codellama", 
        "name": "codellama",
        "provider": "ollama",
        "description": "CodeLlama - Code specialist (LOCAL)"
    },
    "4": {
        "key": "deepseek",
        "name": "deepseek-coder",
        "provider": "ollama",
        "description": "DeepSeek Coder (LOCAL)"
    },
    "5": {
        "key": "qwen",
        "name": "qwen2.5-coder",
        "provider": "ollama",
        "description": "Qwen 2.5 Coder (LOCAL)"
    },
    "6": {
        "key": "mistral",
        "name": "mistral",
        "provider": "ollama",
        "description": "Mistral - Efficient (LOCAL)"
    },
    "7": {
        "key": "phi3",
        "name": "phi3",
        "provider": "ollama",
        "description": "Phi-3 - Lightweight (LOCAL)"
    }
}

DEFAULT_MODEL = "1"
MAX_ITERATIONS = 10

# Console with UTF-8 support - auto-detect width
def get_terminal_width():
    try:
        return os.get_terminal_size().columns
    except:
        return 100

console = Console(force_terminal=True, width=get_terminal_width()) if RICH_AVAILABLE else None

# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM CONTROL
# ═══════════════════════════════════════════════════════════════════════════════

class SystemControl:
    """System control for the local machine."""
    
    @staticmethod
    def get_system_status() -> dict:
        """Get comprehensive system status."""
        status = {
            "device": DEVICE_NAME,
            "os": f"{platform.system()} {platform.release()}",
            "hostname": socket.gethostname(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "uptime": "Unknown"
        }
        
        if PSUTIL_AVAILABLE:
            # CPU
            status["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            status["cpu_cores"] = psutil.cpu_count()
            
            # Memory
            mem = psutil.virtual_memory()
            status["memory_total_gb"] = round(mem.total / (1024**3), 1)
            status["memory_used_gb"] = round(mem.used / (1024**3), 1)
            status["memory_percent"] = mem.percent
            
            # Disk
            disk = psutil.disk_usage('/')
            status["disk_total_gb"] = round(disk.total / (1024**3), 1)
            status["disk_free_gb"] = round(disk.free / (1024**3), 1)
            status["disk_percent"] = disk.percent
            
            # Battery
            battery = psutil.sensors_battery()
            if battery:
                status["battery_percent"] = battery.percent
                status["battery_plugged"] = battery.power_plugged
                if battery.secsleft > 0:
                    hours = battery.secsleft // 3600
                    mins = (battery.secsleft % 3600) // 60
                    status["battery_time_left"] = f"{hours}h {mins}m"
            
            # Network
            net = psutil.net_io_counters()
            status["network_sent_mb"] = round(net.bytes_sent / (1024**2), 1)
            status["network_recv_mb"] = round(net.bytes_recv / (1024**2), 1)
            
            # Uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            hours = int(uptime.total_seconds() // 3600)
            mins = int((uptime.total_seconds() % 3600) // 60)
            status["uptime"] = f"{hours}h {mins}m"
        
        return status
    
    @staticmethod
    def get_running_apps() -> List[dict]:
        """Get list of running applications."""
        apps = []
        if PSUTIL_AVAILABLE:
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
                try:
                    info = proc.info
                    if info['memory_percent'] and info['memory_percent'] > 0.1:
                        apps.append({
                            "name": info['name'],
                            "pid": info['pid'],
                            "memory": round(info['memory_percent'], 1),
                            "cpu": round(info['cpu_percent'] or 0, 1)
                        })
                except:
                    pass
            apps.sort(key=lambda x: x['memory'], reverse=True)
        return apps[:15]
    
    @staticmethod
    def open_app(app_name: str) -> str:
        """Open an application."""
        common_apps = {
            "notepad": "notepad.exe",
            "chrome": "chrome",
            "firefox": "firefox",
            "edge": "msedge",
            "word": "winword",
            "excel": "excel",
            "powerpoint": "powerpnt",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "terminal": "wt.exe",
            "powershell": "powershell.exe",
            "explorer": "explorer.exe",
            "settings": "ms-settings:",
            "task manager": "taskmgr.exe",
            "spotify": "spotify",
            "vlc": "vlc",
            "vscode": "code",
            "vs code": "code",
        }
        
        app = common_apps.get(app_name.lower(), app_name)
        
        try:
            if app.startswith("ms-"):
                os.system(f"start {app}")
            else:
                subprocess.Popen(app, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opening {app_name} on {DEVICE_NAME}"
        except Exception as e:
            return f"Failed to open {app_name}: {e}"
    
    @staticmethod
    def close_app(app_name: str) -> str:
        """Close an application."""
        try:
            if platform.system() == 'Windows':
                # Try to close gracefully first
                result = subprocess.run(f'taskkill /IM "{app_name}" /F', 
                                        shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    return f"Closed {app_name}"
                else:
                    return f"Could not find {app_name}"
            else:
                subprocess.run(['pkill', app_name])
                return f"Closed {app_name}"
        except Exception as e:
            return f"Error closing {app_name}: {e}"
    
    @staticmethod
    def lock_screen() -> str:
        """Lock the screen."""
        if platform.system() == 'Windows':
            ctypes.windll.user32.LockWorkStation()
            return f"Locking {DEVICE_NAME}"
        else:
            os.system("gnome-screensaver-command -l")
            return f"Locking {DEVICE_NAME}"
    
    @staticmethod
    def shutdown(restart: bool = False) -> str:
        """Shutdown or restart the system."""
        if platform.system() == 'Windows':
            cmd = "shutdown /r /t 30" if restart else "shutdown /s /t 30"
            os.system(cmd)
            action = "restarting" if restart else "shutting down"
            return f"{DEVICE_NAME} will be {action} in 30 seconds. Run 'shutdown /a' to cancel."
        return "Shutdown command not available on this platform."
    
    @staticmethod
    def cancel_shutdown() -> str:
        """Cancel scheduled shutdown."""
        if platform.system() == 'Windows':
            os.system("shutdown /a")
            return "Shutdown cancelled."
        return "No shutdown to cancel."
    
    @staticmethod
    def set_volume(level: int) -> str:
        """Set system volume (0-100)."""
        if platform.system() == 'Windows' and CTYPES_AVAILABLE:
            try:
                # Use nircmd if available, otherwise use PowerShell
                ps_cmd = f'(New-Object -ComObject WScript.Shell).SendKeys([char]173)' if level == 0 else \
                         f'$obj = New-Object -ComObject WScript.Shell; 1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}; 1..{level//2} | ForEach-Object {{ $obj.SendKeys([char]175) }}'
                return f"Volume set to {level}% (use system controls for precise adjustment)"
            except:
                pass
        return f"Volume control requires manual adjustment. Set to: {level}%"
    
    @staticmethod
    def get_ip_addresses() -> dict:
        """Get local and public IP addresses."""
        ips = {"local": [], "hostname": socket.gethostname()}
        
        # Get local IPs
        for interface, addrs in psutil.net_if_addrs().items() if PSUTIL_AVAILABLE else []:
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                    ips["local"].append({"interface": interface, "ip": addr.address})
        
        return ips
    
    @staticmethod
    def take_screenshot(filename: str = None) -> str:
        """Take a screenshot."""
        try:
            if not filename:
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            if platform.system() == 'Windows':
                # Use PowerShell to take screenshot
                ps_script = f'''
                Add-Type -AssemblyName System.Windows.Forms
                $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
                $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
                $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
                $bitmap.Save("{os.path.abspath(filename)}")
                '''
                subprocess.run(['powershell', '-Command', ps_script], capture_output=True)
                return f"Screenshot saved to {filename}"
            return "Screenshot requires Windows."
        except Exception as e:
            return f"Screenshot failed: {e}"
    
    @staticmethod
    def search_files(query: str, directory: str = None) -> List[str]:
        """Search for files."""
        if not directory:
            directory = os.path.expanduser("~")
        
        results = []
        try:
            for root, dirs, files in os.walk(directory):
                # Skip hidden and system directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'AppData']]
                for file in files:
                    if query.lower() in file.lower():
                        results.append(os.path.join(root, file))
                if len(results) >= 20:
                    break
        except:
            pass
        return results[:20]

# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS FOR CODING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ToolResult:
    success: bool
    output: str
    data: Any = None

class Tool(ABC):
    name: str
    description: str
    parameters: Dict[str, Any]
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        pass

class ReadFileTool(Tool):
    name = "read_file"
    description = "Read contents of a file"
    parameters = {"file_path": {"type": "string", "description": "Path to the file"}}
    
    def execute(self, file_path: str) -> ToolResult:
        try:
            path = os.path.abspath(file_path)
            if not os.path.exists(path):
                return ToolResult(False, f"File not found: {path}")
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return ToolResult(True, content[:15000], {"path": path, "lines": content.count('\n')})
        except Exception as e:
            return ToolResult(False, f"Error: {e}")

class WriteFileTool(Tool):
    name = "write_file"
    description = "Write or create a file"
    parameters = {
        "file_path": {"type": "string", "description": "Path to the file"},
        "content": {"type": "string", "description": "Content to write"}
    }
    
    def execute(self, file_path: str, content: str) -> ToolResult:
        try:
            path = os.path.abspath(file_path)
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return ToolResult(True, f"Written to {path} ({len(content)} chars)")
        except Exception as e:
            return ToolResult(False, f"Error: {e}")

class ListDirTool(Tool):
    name = "list_dir"
    description = "List directory contents"
    parameters = {"path": {"type": "string", "description": "Directory path"}}
    
    def execute(self, path: str = ".") -> ToolResult:
        try:
            abs_path = os.path.abspath(path)
            items = []
            for item in os.listdir(abs_path):
                item_path = os.path.join(abs_path, item)
                is_dir = os.path.isdir(item_path)
                size = os.path.getsize(item_path) if not is_dir else 0
                items.append({"name": item, "type": "dir" if is_dir else "file", "size": size})
            return ToolResult(True, json.dumps(items, indent=2), items)
        except Exception as e:
            return ToolResult(False, f"Error: {e}")

class RunCommandTool(Tool):
    name = "run_command"
    description = "Execute a shell command"
    parameters = {"command": {"type": "string", "description": "Command to run"}}
    
    def execute(self, command: str) -> ToolResult:
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
            )
            output = result.stdout + result.stderr
            return ToolResult(result.returncode == 0, output.strip() or "Done")
        except subprocess.TimeoutExpired:
            return ToolResult(False, "Command timed out")
        except Exception as e:
            return ToolResult(False, f"Error: {e}")

class SystemStatusTool(Tool):
    name = "system_status"
    description = "Get current system status"
    parameters = {}
    
    def execute(self) -> ToolResult:
        status = SystemControl.get_system_status()
        return ToolResult(True, json.dumps(status, indent=2), status)

class OpenAppTool(Tool):
    name = "open_app"
    description = "Open an application"
    parameters = {"app_name": {"type": "string", "description": "Name of the app to open"}}
    
    def execute(self, app_name: str) -> ToolResult:
        result = SystemControl.open_app(app_name)
        return ToolResult(True, result)

class CloseAppTool(Tool):
    name = "close_app"
    description = "Close an application"
    parameters = {"app_name": {"type": "string", "description": "Name of the process to close"}}
    
    def execute(self, app_name: str) -> ToolResult:
        result = SystemControl.close_app(app_name)
        return ToolResult(True, result)

class LockScreenTool(Tool):
    name = "lock_screen"
    description = "Lock the screen"
    parameters = {}
    
    def execute(self) -> ToolResult:
        result = SystemControl.lock_screen()
        return ToolResult(True, result)

class SearchFilesTool(Tool):
    name = "search_files"
    description = "Search for files"
    parameters = {
        "query": {"type": "string", "description": "Search query"}
    }
    
    def execute(self, query: str) -> ToolResult:
        results = SystemControl.search_files(query)
        return ToolResult(True, json.dumps(results, indent=2), results)

class PythonExecTool(Tool):
    name = "python_exec"
    description = "Execute Python code"
    parameters = {"code": {"type": "string", "description": "Python code to run"}}
    
    def execute(self, code: str) -> ToolResult:
        try:
            local_vars = {}
            exec(code, {"__builtins__": __builtins__}, local_vars)
            result = local_vars.get('result', str(local_vars) if local_vars else "Executed")
            return ToolResult(True, str(result))
        except Exception as e:
            return ToolResult(False, f"Error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# NOVA AI ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class Nova:
    """NOVA - Advanced AI Coding Assistant"""
    
    def __init__(self):
        self.gemini_key = None
        self.hf_key = None
        self.current_model = DEFAULT_MODEL
        self.model = None
        self.hf_client = None
        self.tools = self._init_tools()
        self.history = []
        self.ollama_history = []  # Conversation memory for Ollama
        self.cwd = os.getcwd()
        self.system_control = SystemControl()
        
    def _init_tools(self) -> Dict[str, Tool]:
        tools = [
            ReadFileTool(),
            WriteFileTool(),
            ListDirTool(),
            RunCommandTool(),
            SystemStatusTool(),
            OpenAppTool(),
            CloseAppTool(),
            LockScreenTool(),
            SearchFilesTool(),
            PythonExecTool(),
        ]
        return {t.name: t for t in tools}
    
    def initialize(self, gemini_key: str = None, hf_key: str = None) -> bool:
        """Initialize NOVA - tries Ollama first (local), then Gemini."""
        self.gemini_key = gemini_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        # Load from .env file
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if "=" in line:
                        key, val = line.strip().split("=", 1)
                        val = val.strip('"').strip("'")
                        if "GEMINI" in key or "GOOGLE" in key:
                            self.gemini_key = self.gemini_key or val
        
        # Use Ollama (local)
        if self._check_ollama():
            # Try to auto-select an installed model
            installed_models = self._get_ollama_models()
            model_selected = False
            
            # Check if any configured model is installed
            for key, info in MODELS.items():
                if info["provider"] == "ollama":
                    if any(m.split(':')[0] == info["name"].split(':')[0] for m in installed_models):
                        self.current_model = key
                        model_selected = True
                        break
            
            if not model_selected:
                self.current_model = "1"  # Default to llama3.2
                
            return True
        
        print("[X] Ollama is not running!")
        print("  1. Install Ollama: https://ollama.ai")
        print("  2. Run: ollama serve")
        print("  3. Pull a model: ollama pull llama3.2")
        return False
    
    def _start_ollama(self):
        """Try to start Ollama server automatically."""
        try:
            import time
            # Start ollama serve in background
            if sys.platform == 'win32':
                subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            # Wait for it to start
            for _ in range(10):
                time.sleep(0.5)
                if self._check_ollama_quick():
                    return True
            return False
        except:
            return False
    
    def _check_ollama_quick(self) -> bool:
        """Quick check if Ollama is running (no auto-start)."""
        try:
            import urllib.request
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=1) as resp:
                return resp.status == 200
        except:
            return False
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running, try to start if not."""
        # First quick check
        if self._check_ollama_quick():
            return True
        
        # Try to start Ollama
        print("  Starting Ollama server...")
        if self._start_ollama():
            print("  [OK] Ollama started!")
            return True
        
        return False

    def _get_ollama_models(self) -> List[str]:
        """Get list of installed Ollama models."""
        try:
            import urllib.request
            import json as json_lib
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json_lib.loads(resp.read().decode())
                return [m['name'] for m in data.get('models', [])]
        except:
            return []
    
    def _init_gemini_model(self):
        """Initialize the Gemini model with tools."""
        model_config = MODELS[self.current_model]
        
        tool_declarations = []
        for tool in self.tools.values():
            tool_declarations.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": tool.parameters,
                    "required": list(tool.parameters.keys()) if tool.parameters else []
                }
            })
        
        system_prompt = f"""You are NOVA, an advanced AI assistant for {DEVICE_NAME}.
You help control the computer, manage files, run code, and assist with any task.

CAPABILITIES:
- Control {DEVICE_NAME}: open/close apps, lock screen, get system status
- Read, write, and search files
- Execute commands and Python code
- Answer questions and help with coding

PERSONALITY:
- Professional but friendly
- Proactive and helpful
- Address the user respectfully
- Be concise but thorough

When asked about system status, apps, or computer control, use the appropriate tools.
You can open apps, close them, check system resources, and more."""

        self.model = genai.GenerativeModel(
            model_name=model_config["name"],
            system_instruction=system_prompt,
            tools=[{"function_declarations": tool_declarations}] if tool_declarations else None,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=8192,
            )
        )
    
    def set_model(self, model_num: str) -> bool:
        if model_num not in MODELS:
            return False
        model_config = MODELS[model_num]
        if model_config["provider"] == "google" and self.gemini_key:
            self.current_model = model_num
            self._init_gemini_model()
            return True
        elif model_config["provider"] == "ollama":
            self.current_model = model_num
            return True
        return False
    
    def get_current_model_info(self) -> dict:
        return MODELS[self.current_model]
    
    def _execute_tool(self, tool_name: str, args: dict) -> str:
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found"
        
        print(f"  -> {tool_name}: {str(args)[:60]}...")
        result = self.tools[tool_name].execute(**args)
        status = "[OK]" if result.success else "[X]"
        print(f"  {status} {result.output[:80]}...")
        return result.output
    
    def process(self, user_input: str) -> str:
        model_config = MODELS[self.current_model]
        status = self.system_control.get_system_status()
        context = f"Device: {DEVICE_NAME}\nTime: {status['time']}\nBattery: {status.get('battery_percent', 'N/A')}%"
        full_prompt = f"{context}\n\nUser: {user_input}"
        
        if model_config["provider"] == "google":
            return self._process_gemini(full_prompt)
        elif model_config["provider"] == "ollama":
            return self._process_ollama(user_input)
        else:
            return "No AI backend available"
    
    def _process_gemini(self, prompt: str) -> str:
        if not self.model:
            return "Model not initialized"
        
        chat = self.model.start_chat(history=[])
        iterations = 0
        current_prompt = prompt
        final_response = ""
        
        while iterations < MAX_ITERATIONS:
            iterations += 1
            
            try:
                response = chat.send_message(current_prompt)
                
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        tool_result = self._execute_tool(fc.name, dict(fc.args) if fc.args else {})
                        current_prompt = f"Tool '{fc.name}' result:\n{tool_result}\n\nContinue with the task."
                        continue
                    
                    if hasattr(part, 'text') and part.text:
                        final_response = part.text
                
                has_function_call = any(
                    hasattr(p, 'function_call') and p.function_call 
                    for p in response.candidates[0].content.parts
                )
                if not has_function_call and final_response:
                    break
                    
            except Exception as e:
                return f"Error: {e}"
        
        self.history.append({"input": prompt, "output": final_response})
        return final_response
    
    def _process_huggingface(self, prompt: str) -> str:
        if not self.hf_client:
            return "HuggingFace client not initialized"
        
        model_name = MODELS[self.current_model]["name"]
        
        try:
            messages = [
                {"role": "system", "content": f"You are NOVA, an AI assistant for {DEVICE_NAME}."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.hf_client.chat_completion(
                model=model_name,
                messages=messages,
                max_tokens=4096,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error: {e}"
    
    def _process_ollama(self, prompt: str) -> str:
        """Process with local Ollama - with tool execution."""
        model_name = MODELS[self.current_model]["name"]
        
        # Build tool descriptions for the AI
        tool_info = """
AVAILABLE TOOLS - Use EXACT format:

=== FILE OPERATIONS ===
[TOOL:write_file] filepath|content
  Example: [TOOL:write_file] hello.py|print("Hello World")

[TOOL:read_file] filepath
  Example: [TOOL:read_file] main.py

[TOOL:view_file] filepath|start|end
  View with line numbers
  Example: [TOOL:view_file] app.py|1|50

[TOOL:edit_file] filepath|start|end|new_content
  Edit lines (use \\n for newlines)
  Example: [TOOL:edit_file] main.py|5|5|print("Hello")

[TOOL:append_file] filepath|content
  Example: [TOOL:append_file] log.txt|Entry

[TOOL:list_dir] path
  Example: [TOOL:list_dir] .

[TOOL:search_files] query
  Example: [TOOL:search_files] .py

=== CODE EXECUTION ===
[TOOL:run_python] code_or_file
  Example: [TOOL:run_python] print(2+2)
  Example: [TOOL:run_python] main.py

[TOOL:run_command] command
  Example: [TOOL:run_command] npm install

=== PROJECTS ===
[TOOL:create_project] name|type
  Types: python, web
  Example: [TOOL:create_project] myapp|python

=== SYSTEM ===
[TOOL:open_app] app
[TOOL:close_app] app
[TOOL:system_status]
[TOOL:lock_screen]

WORKFLOW: view_file -> edit_file -> run_python
"""
        
        system_prompt = f"""You are NOVA, a friendly and helpful AI assistant running on {DEVICE_NAME}.

You can have natural conversations AND execute actions on this computer.

{tool_info}

RULES:
1. For GREETINGS and CONVERSATION (like "hi", "hello", "how are you", "thanks"): 
   Respond naturally and warmly. Be friendly and conversational. DO NOT use tools for casual chat.
   
2. For ACTION REQUESTS (like "open chrome", "check status", "run command"):
   USE THE APPROPRIATE TOOL from the list above. Don't just describe - actually do it.

3. Be helpful, friendly, and concise
4. After using a tool, briefly confirm what you did

Current device: {DEVICE_NAME}"""
        
        try:
            import urllib.request
            import json as json_lib
            import re
            
            # Build messages with conversation history
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history (keep last 10 exchanges to avoid context overflow)
            for exchange in self.ollama_history[-10:]:
                messages.append({"role": "user", "content": exchange["user"]})
                messages.append({"role": "assistant", "content": exchange["assistant"]})
            
            # Add current prompt
            messages.append({"role": "user", "content": prompt})
            
            data = json_lib.dumps({
                "model": model_name,
                "messages": messages,
                "stream": False
            }).encode()
            
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json_lib.loads(resp.read().decode())
                response_text = result.get("message", {}).get("content", "No response")
            
            # Parse and execute tool calls
            tool_pattern = r'\[TOOL:(\w+)\]\s*(.*)' 
            matches = re.findall(tool_pattern, response_text)
            
            final_response = response_text
            if matches:
                results = []
                for tool_name, args in matches:
                    # Debug: show what's being executed
                    print(f"  -> Executing: [{tool_name}] with args: '{args}'")
                    tool_result = self._execute_ollama_tool(tool_name, args.strip())
                    results.append(f"[{tool_name}] {tool_result}")
                
                # Clean response and add results
                clean_response = re.sub(tool_pattern, '', response_text).strip()
                if clean_response:
                    final_response = f"{clean_response}\n\n" + "\n".join(results)
                else:
                    final_response = "\n".join(results)
            
            # Save to conversation history
            self.ollama_history.append({
                "user": prompt,
                "assistant": final_response
            })
            
            return final_response
                
        except urllib.error.URLError:
            return "Error: Ollama is not running. Start it with 'ollama serve'"
        except Exception as e:
            return f"Error: {e}"
    
    def _execute_ollama_tool(self, tool_name: str, args: str) -> str:
        """Execute a tool call from Ollama response."""
        try:
            if tool_name == "open_app":
                result = SystemControl.open_application(args)
                return f"Opened {args}" if result else f"Failed to open {args}"
            
            elif tool_name == "close_app":
                result = SystemControl.close_application(args)
                return f"Closed {args}" if result else f"Failed to close {args}"
            
            elif tool_name == "system_status":
                status = SystemControl.get_system_status()
                return f"CPU: {status.get('cpu_percent')}%, Memory: {status.get('memory_percent')}%, Battery: {status.get('battery_percent', 'N/A')}%"
            
            elif tool_name == "lock_screen":
                SystemControl.lock_screen()
                return "Screen locked"
            
            elif tool_name == "run_command":
                result = subprocess.run(args, shell=True, capture_output=True, text=True, timeout=30)
                output = result.stdout or result.stderr
                return output[:500] if output else "Command executed"
            
            elif tool_name == "read_file":
                if os.path.exists(args):
                    with open(args, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return content[:1000] + "..." if len(content) > 1000 else content
                return f"File not found: {args}"
            
            elif tool_name == "write_file":
                if "|" in args:
                    path, content = args.split("|", 1)
                    with open(path.strip(), 'w', encoding='utf-8') as f:
                        f.write(content.strip())
                    return f"Written to {path.strip()}"
                return "Format: path|content"
            
            elif tool_name == "list_dir":
                path = args or "."
                if os.path.isdir(path):
                    items = os.listdir(path)[:20]
                    return ", ".join(items)
                return f"Directory not found: {path}"
            
            elif tool_name == "search_files":
                results = SystemControl.search_files(args)
                return ", ".join(results[:5]) if results else "No files found"
            
            elif tool_name == "view_file":
                # View file with line numbers: view_file path|start_line|end_line
                parts = args.split("|")
                path = parts[0].strip()
                start_line = int(parts[1]) if len(parts) > 1 else 1
                end_line = int(parts[2]) if len(parts) > 2 else start_line + 50
                
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                    total_lines = len(lines)
                    start_line = max(1, start_line)
                    end_line = min(total_lines, end_line)
                    
                    output = f"File: {path} ({total_lines} lines)\n"
                    output += "-" * 40 + "\n"
                    for i in range(start_line - 1, end_line):
                        output += f"{i+1:4}: {lines[i]}"
                    return output
                return f"File not found: {path}"
            
            elif tool_name == "edit_file":
                # Edit specific lines: edit_file path|start_line|end_line|new_content
                parts = args.split("|", 3)
                if len(parts) < 4:
                    return "Format: edit_file path|start_line|end_line|new_content"
                
                path = parts[0].strip()
                start_line = int(parts[1])
                end_line = int(parts[2])
                new_content = parts[3]
                
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Replace lines
                    new_lines = new_content.split("\\n")
                    lines[start_line-1:end_line] = [line + "\n" for line in new_lines]
                    
                    with open(path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    
                    return f"Edited {path} (lines {start_line}-{end_line})"
                return f"File not found: {path}"
            
            elif tool_name == "run_python":
                # Run Python code or file
                if args.endswith('.py') and os.path.exists(args):
                    result = subprocess.run(['python', args], capture_output=True, text=True, timeout=30)
                else:
                    # Run code directly
                    result = subprocess.run(['python', '-c', args], capture_output=True, text=True, timeout=30)
                
                output = result.stdout if result.stdout else ""
                if result.stderr:
                    output += f"\nError: {result.stderr}"
                return output[:1000] if output else "Code executed (no output)"
            
            elif tool_name == "append_file":
                # Append to file: append_file path|content
                if "|" in args:
                    path, content = args.split("|", 1)
                    with open(path.strip(), 'a', encoding='utf-8') as f:
                        f.write(content.strip() + "\n")
                    return f"Appended to {path.strip()}"
                return "Format: append_file path|content"
            
            elif tool_name == "create_project":
                # Create project structure: create_project name|type (python/web/node)
                parts = args.split("|")
                name = parts[0].strip()
                proj_type = parts[1].strip() if len(parts) > 1 else "python"
                
                os.makedirs(name, exist_ok=True)
                
                if proj_type == "python":
                    # Create Python project structure
                    with open(f"{name}/main.py", 'w') as f:
                        f.write('#!/usr/bin/env python3\n\ndef main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()\n')
                    with open(f"{name}/requirements.txt", 'w') as f:
                        f.write('# Add your dependencies here\n')
                    with open(f"{name}/README.md", 'w') as f:
                        f.write(f'# {name}\n\nA Python project.\n\n## Usage\n\n```bash\npython main.py\n```\n')
                    return f"Created Python project: {name}/"
                
                elif proj_type == "web":
                    # Create web project
                    with open(f"{name}/index.html", 'w') as f:
                        f.write(f'<!DOCTYPE html>\n<html>\n<head>\n    <title>{name}</title>\n    <link rel="stylesheet" href="style.css">\n</head>\n<body>\n    <h1>{name}</h1>\n    <script src="app.js"></script>\n</body>\n</html>\n')
                    with open(f"{name}/style.css", 'w') as f:
                        f.write('body {\n    font-family: Arial, sans-serif;\n    margin: 0;\n    padding: 20px;\n}\n')
                    with open(f"{name}/app.js", 'w') as f:
                        f.write('console.log("Hello from " + document.title);\n')
                    return f"Created web project: {name}/"
                
                return f"Created directory: {name}/"
            
            else:
                return f"Unknown tool: {tool_name}"
                
        except Exception as e:
            return f"Tool error: {e}"

# ═══════════════════════════════════════════════════════════════════════════════
# WEB SERVER FOR PHONE ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

class NovaWebHandler(BaseHTTPRequestHandler):
    nova_instance = None
    
    def log_message(self, format, *args):
        pass  # Suppress logs
    
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self._get_html().encode())
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status = SystemControl.get_system_status()
            self.wfile.write(json.dumps(status).encode())
        elif self.path == "/api/apps":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            apps = SystemControl.get_running_apps()
            self.wfile.write(json.dumps(apps).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        if self.path == "/api/chat":
            try:
                data = json.loads(post_data)
                message = data.get("message", "")
                
                if NovaWebHandler.nova_instance:
                    response = NovaWebHandler.nova_instance.process(message)
                else:
                    response = "NOVA not initialized"
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"response": response}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        elif self.path == "/api/command":
            try:
                data = json.loads(post_data)
                cmd = data.get("command", "")
                
                result = ""
                if cmd == "lock":
                    result = SystemControl.lock_screen()
                elif cmd == "shutdown":
                    result = SystemControl.shutdown()
                elif cmd == "restart":
                    result = SystemControl.shutdown(restart=True)
                elif cmd.startswith("open:"):
                    app = cmd.split(":", 1)[1]
                    result = SystemControl.open_app(app)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"result": result}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def _get_html(self):
        return '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NOVA - Remote Control</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0a0a0a, #1a1a2e);
            color: #00d4ff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid #00d4ff33;
            margin-bottom: 20px;
        }
        .header h1 { font-size: 3em; text-shadow: 0 0 20px #00d4ff; }
        .header p { color: #888; margin-top: 10px; }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .status-card {
            background: #ffffff11;
            border: 1px solid #00d4ff33;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }
        .status-card h3 { font-size: 0.9em; color: #888; }
        .status-card .value { font-size: 1.5em; margin-top: 5px; }
        .chat-box {
            background: #ffffff11;
            border: 1px solid #00d4ff33;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .chat-messages {
            height: 300px;
            overflow-y: auto;
            margin-bottom: 15px;
            padding: 10px;
        }
        .message { margin-bottom: 10px; padding: 10px; border-radius: 8px; }
        .message.user { background: #00d4ff22; margin-left: 20%; }
        .message.nova { background: #ffffff11; margin-right: 20%; }
        .input-row { display: flex; gap: 10px; }
        .input-row input {
            flex: 1;
            padding: 12px;
            border: 1px solid #00d4ff33;
            border-radius: 8px;
            background: #0a0a0a;
            color: #00d4ff;
            font-size: 1em;
        }
        button {
            padding: 12px 25px;
            background: linear-gradient(135deg, #00d4ff, #0088ff);
            border: none;
            border-radius: 8px;
            color: #000;
            font-weight: bold;
            cursor: pointer;
        }
        button:hover { opacity: 0.9; }
        .quick-actions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
        }
        .quick-actions button { background: #ffffff22; color: #00d4ff; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>NOVA</h1>
            <p>Remote Control for ''' + DEVICE_NAME + '''</p>
        </div>
        
        <div class="status-grid" id="status">
            <div class="status-card"><h3>CPU</h3><div class="value" id="cpu">--%</div></div>
            <div class="status-card"><h3>Memory</h3><div class="value" id="memory">--%</div></div>
            <div class="status-card"><h3>Battery</h3><div class="value" id="battery">--%</div></div>
            <div class="status-card"><h3>Uptime</h3><div class="value" id="uptime">--</div></div>
        </div>
        
        <div class="chat-box">
            <div class="chat-messages" id="messages"></div>
            <div class="input-row">
                <input type="text" id="input" placeholder="Ask NOVA anything..." onkeypress="if(event.key==='Enter')sendMessage()">
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
        
        <div class="quick-actions">
            <button onclick="sendCommand('lock')">Lock Screen</button>
            <button onclick="sendCommand('open:notepad')">Notepad</button>
            <button onclick="sendCommand('open:chrome')">Chrome</button>
            <button onclick="sendCommand('open:explorer')">Explorer</button>
        </div>
    </div>
    
    <script>
        function updateStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('cpu').textContent = (data.cpu_percent || 0) + '%';
                    document.getElementById('memory').textContent = (data.memory_percent || 0) + '%';
                    document.getElementById('battery').textContent = (data.battery_percent || '--') + '%';
                    document.getElementById('uptime').textContent = data.uptime || '--';
                });
        }
        
        function sendMessage() {
            const input = document.getElementById('input');
            const msg = input.value.trim();
            if (!msg) return;
            
            addMessage(msg, 'user');
            input.value = '';
            
            fetch('/api/chat', {
                method: 'POST',
                body: JSON.stringify({message: msg})
            })
            .then(r => r.json())
            .then(data => addMessage(data.response, 'nova'));
        }
        
        function addMessage(text, type) {
            const div = document.createElement('div');
            div.className = 'message ' + type;
            div.textContent = text;
            document.getElementById('messages').appendChild(div);
            div.scrollIntoView();
        }
        
        function sendCommand(cmd) {
            fetch('/api/command', {
                method: 'POST',
                body: JSON.stringify({command: cmd})
            })
            .then(r => r.json())
            .then(data => addMessage(data.result, 'nova'));
        }
        
        updateStatus();
        setInterval(updateStatus, 5000);
    </script>
</body>
</html>'''

# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class NovaCLI:
    def __init__(self):
        self.nova = Nova()
        self.web_server = None
        self.bluetooth_server = None
        self.nie = NeuralIntentEngine() if NIE_AVAILABLE else None
        
    def print_banner(self):
        """Print the NOVA banner - responsive to terminal width."""
        width = get_terminal_width()
        
        # Use compact banner for narrow terminals
        if width < 60:
            banner_text = """
 ╔═══════════════════════════╗
 ║   NOVA v{version}              ║
 ║   AI Coding Assistant     ║
 ╚═══════════════════════════╝
"""
        else:
            banner_text = """
    ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗
    ████╗  ██║██╔═══██╗██║   ██║██╔══██╗
    ██╔██╗ ██║██║   ██║██║   ██║███████║
    ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║
    ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║
    ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝

         Advanced AI Coding Assistant v{version}
"""
        
        if RICH_AVAILABLE and console:
            # Update console width
            console.width = width
            styled_text = f"[bold bright_cyan]{banner_text.format(version=NOVA_VERSION)}[/]"
            banner_panel = Panel(
                Align.center(styled_text),
                border_style="bright_cyan",
                box=box.DOUBLE,
                padding=(0, 1)
            )
            console.print(banner_panel)
        else:
            print("=" * min(width, 60))
            print(banner_text.format(version=NOVA_VERSION))
            print("=" * min(width, 60))
    
    def print_status(self):
        """Print system status."""
        status = SystemControl.get_system_status()
        
        if RICH_AVAILABLE and console:
            table = Table(box=box.SIMPLE, border_style="cyan", show_header=False)
            table.add_column("", style="dim")
            table.add_column("", style="bright_white")
            
            table.add_row("Device", f"{status['device']} ({status['hostname']})")
            table.add_row("OS", status['os'])
            table.add_row("CPU", f"{status.get('cpu_percent', 'N/A')}% ({status.get('cpu_cores', '?')} cores)")
            table.add_row("Memory", f"{status.get('memory_percent', 'N/A')}% ({status.get('memory_used_gb', '?')}GB / {status.get('memory_total_gb', '?')}GB)")
            if 'battery_percent' in status:
                bat = f"{status['battery_percent']}%"
                if status.get('battery_plugged'):
                    bat += " [Charging]"
                elif status.get('battery_time_left'):
                    bat += f" ({status['battery_time_left']})"
                table.add_row("Battery", bat)
            table.add_row("Uptime", status['uptime'])
            
            console.print(table)
        else:
            print(f"\n  Device: {status['device']}")
            print(f"  CPU: {status.get('cpu_percent', 'N/A')}%")
            print(f"  Memory: {status.get('memory_percent', 'N/A')}%")
            print(f"  Battery: {status.get('battery_percent', 'N/A')}%")
    
    def start_web_server(self, quiet=False):
        """Start the web server for phone access."""
        NovaWebHandler.nova_instance = self.nova
        
        ips = SystemControl.get_ip_addresses()
        local_ip = ips['local'][0]['ip'] if ips['local'] else 'localhost'
        self.local_ip = local_ip
        
        try:
            server = HTTPServer(('0.0.0.0', WEB_PORT), NovaWebHandler)
            
            if not quiet:
                if RICH_AVAILABLE and console:
                    console.print(f"\n  [green][OK][/] Web server started!")
                    console.print(f"  [cyan]Local:[/] http://localhost:{WEB_PORT}")
                    console.print(f"  [cyan]Network:[/] http://{local_ip}:{WEB_PORT}")
                    console.print(f"  [dim]Access from your phone on the same network[/]\n")
                else:
                    print(f"\n  Web server: http://{local_ip}:{WEB_PORT}\n")
            
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.web_server = server
            return server
        except Exception as e:
            print(f"  Web server failed: {e}")
            return None
    
    def start_bluetooth_server(self):
        """Start the Bluetooth server for phone access."""
        if not BLUETOOTH_AVAILABLE:
            if RICH_AVAILABLE and console:
                console.print("\n  [red][X] Bluetooth module not available![/]")
                console.print("  [dim]Run: pip install pyserial[/]\n")
            else:
                print("\n  Bluetooth module not available!")
                print("  Run: pip install pyserial\n")
            return None
        
        if self.bluetooth_server and self.bluetooth_server.running:
            if RICH_AVAILABLE and console:
                console.print("\n  [yellow]Bluetooth server already running![/]\n")
            else:
                print("\n  Bluetooth server already running!\n")
            return self.bluetooth_server
        
        if RICH_AVAILABLE and console:
            console.print("\n  [cyan]Starting Bluetooth Server...[/]")
            console.print("\n  [dim]Available COM ports:[/]")
        else:
            print("\n  Starting Bluetooth Server...")
            print("\n  Available COM ports:")
        
        # List available ports
        list_com_ports()
        
        # Get port from user
        try:
            if RICH_AVAILABLE:
                port = Prompt.ask("[cyan]Enter COM port (e.g., COM5) or Enter for auto[/]", default="")
            else:
                port = input("Enter COM port (e.g., COM5) or Enter for auto: ").strip()
            
            self.bluetooth_server = BluetoothServer(nova_instance=self.nova)
            
            if port:
                success = self.bluetooth_server.start(port=port)
            else:
                success = self.bluetooth_server.start()
            
            if success:
                if RICH_AVAILABLE and console:
                    console.print("\n  [green][OK] Bluetooth server started![/]")
                    console.print("  [dim]Use 'Serial Bluetooth Terminal' app on your phone[/]\n")
            
            return self.bluetooth_server if success else None
            
        except Exception as e:
            print(f"  Bluetooth server failed: {e}")
            return None
    
    def start_agent_mode(self):
        """Start the MCP Agent mode for code generation and execution."""
        if not AGENT_AVAILABLE:
            if RICH_AVAILABLE and console:
                console.print("\n  [red][X] MCP Agent not available![/]")
                console.print("  [dim]Check if agent/agent.py exists[/]\n")
            else:
                print("\n  MCP Agent not available!")
            return
        
        if RICH_AVAILABLE and console:
            console.print("\n  [cyan]Starting MCP Agent Mode...[/]")
            console.print("  [dim]Type your prompt to generate and execute Python code[/]")
            console.print("  [dim]Type 'exit' or '/back' to return to NOVA[/]\n")
        else:
            print("\n  Starting MCP Agent Mode...")
            print("  Type your prompt to generate and execute Python code")
            print("  Type 'exit' or '/back' to return to NOVA\n")
        
        # Get current model from NOVA
        model_info = self.nova.get_current_model_info()
        model_name = model_info.get("name", "nova")
        
        # Initialize agent (works with both EnhancedMCPAgent and original MCPAgent)
        try:
            agent = MCPAgent(model=model_name)
        except Exception as e:
            print(f"  Error initializing agent: {e}")
            return
        
        while True:
            try:
                if RICH_AVAILABLE and console:
                    console.print("[bold magenta]AGENT>[/] ", end="")
                else:
                    print("AGENT> ", end="")
                
                prompt = input().strip()
                
                if not prompt:
                    continue
                
                if prompt.lower() in ["exit", "/back", "/exit", "quit"]:
                    if RICH_AVAILABLE and console:
                        console.print("\n  [cyan]Returning to NOVA...[/]\n")
                    else:
                        print("\n  Returning to NOVA...\n")
                    break
                
                # Run the agent
                print()
                result = agent.run(prompt)
                
                if RICH_AVAILABLE and console:
                    console.print("\n" + "-" * 50)
                    
                    # Show file path if created
                    if result.get("data") and result["data"].get("filepath"):
                        filepath = result["data"]["filepath"]
                        console.print(f"[bold green]✅ Success:[/] Created and executed {os.path.basename(filepath)}")
                    elif result.get("filepath"):
                        console.print(f"[bold green]✅ Success:[/] Created {os.path.basename(result['filepath'])}")
                    
                    # Show code ONLY if present and not suppressed
                    if result.get("code"):
                        console.print("[bold cyan]📄 Generated Code:[/]")
                        code_lines = result["code"].split("\n")
                        for line in code_lines[:15]:
                            console.print(f"  [dim]{line}[/]")
                        if len(code_lines) > 15:
                            console.print(f"  [dim]... ({len(code_lines) - 15} more lines)[/]")
                    
                    # Show output/result
                    if result.get("output") and result["output"].strip():
                        # If output looks like LLM chatter and we found an action, maybe skip it?
                        # For now, just show it clearly
                        console.print("\n[bold cyan]▶ Result:[/]")
                        console.print(result["output"])
                    
                    # Show errors if any
                    if result.get("errors") and not result.get("success"):
                        console.print(f"\n[bold red]❌ Errors:[/]\n{result['errors']}")
                    
                    console.print("-" * 50 + "\n")
                else:
                    print("\n" + "-" * 50)
                    if result.get("output"):
                        print(f"▶ Result: {result['output']}")
                    print("-" * 50 + "\n")
                
            except KeyboardInterrupt:
                print("\n")
                break
            except Exception as e:
                print(f"  Agent error: {e}\n")
    
    def print_help(self):
        help_text = """
## NOVA Commands

### System Control
- "What's the system status?"
- "Open Chrome / Notepad / VS Code"
- "Close notepad.exe"
- "Lock the screen"
- "Show running apps"
- "Search for files named report"

### Coding
- "Create a Python script..."
- "Read main.py and explain it"
- "Run pytest"

### CLI Commands
| Command | Description |
|---------|-------------|
| `/help` | Show this help |
| `/status` | System status |
| `/model` | Change AI model |
| `/web` | Start web server for phone access |
| `/bluetooth` | Start Bluetooth server for phone access |
| `/agent` | Start MCP Agent (code generation & execution) |
| `/clear` | Clear screen |
| `/exit` | Exit NOVA |
"""
        if RICH_AVAILABLE and console:
            console.print(Markdown(help_text))
        else:
            print(help_text)
    
    def show_model_selector(self):
        """Interactive model selector."""
        if RICH_AVAILABLE and console:
            console.print("\n-----------------------------------------------------------------------")
            console.print("[bold white]                         SELECT AI MODEL[/]")
            console.print("-----------------------------------------------------------------------\n")
            
            table = Table(box=box.ASCII, border_style="cyan", show_header=True, header_style="bold white")
            table.add_column("#", style="bold yellow", width=3)
            table.add_column("Model", style="bright_white", width=25)
            table.add_column("Description", style="dim", width=40)
            table.add_column("", style="green", width=10)
            
            for num, info in MODELS.items():
                current = "<- current" if num == self.nova.current_model else ""
                name = info["name"].split("/")[-1][:25]
                table.add_row(num, name, info["description"], current)
            
            console.print(table)
            console.print()
            
            try:
                choice = Prompt.ask("[cyan]Enter number (or Enter to cancel)[/]", default="")
                if choice and choice in MODELS:
                    if self.nova.set_model(choice):
                        console.print(f"\n[green][OK] Switched to {MODELS[choice]['name'].split('/')[-1]}[/]\n")
                    else:
                        console.print(f"\n[red][X] Cannot use this model[/]\n")
            except:
                pass
        else:
            print("\nModels:")
            for num, info in MODELS.items():
                print(f"  {num}. {info['description']}")
            choice = input("Enter number: ").strip()
            if choice in MODELS:
                self.nova.set_model(choice)
    
    def _handle_neural_intent(self, user_input):
        """Intersects input with the Neural Intent Engine. Returns True if handled."""
        if not self.nie:
            return False
            
        res = self.nie.process_command(user_input)
        
        # We only take over if we are very confident and it's a known system intent
        if res['confidence'] >= 0.75 and res['intent_name'] != "UNKNOWN":
            if RICH_AVAILABLE and console:
                # Beautiful Neural Panel
                title = f"[bold bright_cyan]🧠 Neural Interception[/]"
                content = f"Detected Intent: [bold orange1]{res['intent_name']}[/]\nConfidence: [bold green]{res['confidence']*100:.2f}%[/]\n\nThis command is being handled by your local Neural Engine."
                console.print(Panel(content, title=title, border_style="bright_cyan", padding=(1, 2)))
                
                # Manual Permission Gate for Nova CLI
                if Prompt.ask(f"\n🛡️  [bold yellow]PERMISSION REQUEST[/]\nConfirm execution?", choices=["y", "n"], default="n") == "y":
                    PermissionGate.execute_intent(res['intent_id'])
                    console.print("\n[bold green]✅ Action Executed via Local Brain.[/]\n")
                    return True
                else:
                    console.print("\n[bold red]🚫 Operation Aborted.[/]\n")
                    return True 
            else:
                print(f"\n🧠 Thinking... {res['intent_name']} ({res['confidence']*100:.1f}%)")
                if PermissionGate.ask_permission(res['intent_name'], res['confidence']):
                    PermissionGate.execute_intent(res['intent_id'])
                    return True
                return True
        
        return False

    def run(self):
        """Main CLI loop."""
        # Clear screen and print banner
        os.system('cls' if platform.system() == 'Windows' else 'clear')
        self.print_banner()
        
        if not self.nova.initialize():
            sys.exit(1)
        
        model_info = self.nova.get_current_model_info()
        model_name = model_info["name"].split("/")[-1]
        
        if RICH_AVAILABLE and console:
            console.print(f"  [green][OK][/] Ready! Using {model_name}")
            if self.nie:
                console.print(f"  [cyan][BRAIN][/] Neural Intent Engine Active")
        else:
            print(f"  [OK] Ready! Using {model_name}")
            if self.nie:
                print(f"  [BRAIN] Neural Intent Engine Active")
        
        self.print_status()
        
        # Auto-start web server for phone access
        self.local_ip = "localhost"
        self.start_web_server(quiet=True)
        
        if RICH_AVAILABLE and console:
            console.print(f"\n  Type /help for commands")
            console.print(f"  Phone: http://{self.local_ip}:{WEB_PORT}\n")
        else:
            print(f"\n  Phone access: http://{self.local_ip}:{WEB_PORT}\n")
        
        while True:
            try:
                if RICH_AVAILABLE and console:
                    console.print("[bold cyan]NOVA>[/] ", end="")
                else:
                    print("NOVA> ", end="")
                
                user_input = input().strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith("/"):
                    cmd = user_input.lower().split()[0]
                    
                    if cmd in ["/exit", "/quit", "/q"]:
                        if RICH_AVAILABLE and console:
                            console.print(f"\n  [cyan]Goodbye, sir. {DEVICE_NAME} will be waiting.[/]\n")
                        else:
                            print(f"\n  Goodbye, sir. {DEVICE_NAME} will be waiting.\n")
                        break
                    
                    elif cmd == "/help":
                        self.print_help()
                    
                    elif cmd == "/status":
                        self.print_status()
                    
                    elif cmd == "/model":
                        self.show_model_selector()
                    
                    elif cmd == "/web":
                        self.start_web_server()
                    
                    elif cmd == "/clear":
                        os.system('cls' if platform.system() == 'Windows' else 'clear')
                        self.print_banner()
                    
                    elif cmd == "/bluetooth" or cmd == "/bt":
                        self.start_bluetooth_server()
                    
                    elif cmd == "/agent":
                        self.start_agent_mode()
                    
                    else:
                        print(f"  Unknown command: {cmd}")
                    
                    print()
                    continue
                
                # 1. Neural Interception (Local Brain)
                if self._handle_neural_intent(user_input):
                    continue

                # 2. Process with NOVA (LLM/Agent)
                print()
                if RICH_AVAILABLE and console:
                    with console.status("[bold bright_cyan]  Processing...", spinner="dots"):
                        response = self.nova.process(user_input)
                else:
                    print("  Processing...")
                    response = self.nova.process(user_input)
                
                print()
                if RICH_AVAILABLE and console:
                    console.print(Panel(Markdown(response), title="[bold bright_cyan]NOVA[/]", 
                                        border_style="bright_cyan", padding=(1, 2)))
                else:
                    print(f"  NOVA: {response}")
                print()
                
            except KeyboardInterrupt:
                print("\n")
                if RICH_AVAILABLE and console:
                    console.print("  [yellow]Ctrl+C again or /exit to quit[/]")
                else:
                    print("  Ctrl+C again or /exit to quit")
            except Exception as e:
                print(f"  Error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="NOVA - AI Coding Assistant")
    parser.add_argument("--api-key", "-k", help="Gemini API key")
    parser.add_argument("--hf-token", help="HuggingFace token")
    parser.add_argument("--model", "-m", choices=list(MODELS.keys()), help="Model number (1-6)")
    parser.add_argument("--web", "-w", action="store_true", help="Start with web server")
    parser.add_argument("--version", "-v", action="version", version=f"NOVA v{NOVA_VERSION}")
    parser.add_argument("prompt", nargs="*", help="Run single prompt and exit")
    
    args = parser.parse_args()
    
    if args.api_key:
        os.environ["GEMINI_API_KEY"] = args.api_key
    if args.hf_token:
        os.environ["HF_TOKEN"] = args.hf_token
    
    cli = NovaCLI()
    
    if args.model:
        cli.nova.current_model = args.model
    
    if args.prompt:
        if cli.nova.initialize():
            response = cli.nova.process(" ".join(args.prompt))
            print(response)
        sys.exit(0)
    
    # Start web server if requested
    if args.web:
        if cli.nova.initialize():
            cli.start_web_server()
    
    cli.run()

if __name__ == "__main__":
    main()
