#!/usr/bin/env python3
"""
NOVA ADVANCED TOOLS v2.0 - Powerful tools for Nova
"""
import os, sys, json, time, sqlite3, subprocess, base64, re
from datetime import datetime
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass

try:
    import requests
    REQUESTS_OK = True
except: REQUESTS_OK = False

try:
    from bs4 import BeautifulSoup
    BS4_OK = True
except: BS4_OK = False

try:
    import psutil
    PSUTIL_OK = True
except: PSUTIL_OK = False

@dataclass
class ToolResult:
    success: bool
    data: Any
    error: Optional[str] = None

class WebSearchTool:
    """Search web using DuckDuckGo."""
    name = "web_search"
    
    def execute(self, query: str, num_results: int = 5) -> ToolResult:
        if not REQUESTS_OK or not BS4_OK:
            return ToolResult(False, None, "Missing libraries")
        try:
            r = requests.post("https://html.duckduckgo.com/html/", 
                data={"q": query}, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            soup = BeautifulSoup(r.text, 'html.parser')
            results = []
            for res in soup.select('.result')[:num_results]:
                title = res.select_one('.result__title')
                snippet = res.select_one('.result__snippet')
                if title:
                    results.append({"title": title.get_text(strip=True), 
                        "snippet": snippet.get_text(strip=True) if snippet else ""})
            return ToolResult(True, results)
        except Exception as e:
            return ToolResult(False, None, str(e))

class WebScraperTool:
    """Scrape webpage content."""
    name = "web_scraper"
    
    def execute(self, url: str) -> ToolResult:
        if not REQUESTS_OK or not BS4_OK:
            return ToolResult(False, None, "Missing libraries")
        try:
            r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
            for tag in soup(["script", "style", "nav", "footer"]): tag.decompose()
            text = re.sub(r'\n\s*\n', '\n\n', soup.get_text('\n', strip=True))
            return ToolResult(True, text[:8000])
        except Exception as e:
            return ToolResult(False, None, str(e))

class KnowledgeDB:
    """Persistent SQLite knowledge storage."""
    name = "knowledge_db"
    
    def __init__(self, db_path=None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), "..", "nova_knowledge.db")
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS knowledge 
            (id INTEGER PRIMARY KEY, category TEXT, key TEXT, value TEXT, 
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(category, key))''')
        c.execute('''CREATE TABLE IF NOT EXISTS tasks
            (id INTEGER PRIMARY KEY, task TEXT, result TEXT, success INTEGER, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS code_snippets
            (id INTEGER PRIMARY KEY, name TEXT UNIQUE, code TEXT, language TEXT, description TEXT)''')
        conn.commit()
        conn.close()
    
    def store(self, category: str, key: str, value: Any) -> ToolResult:
        try:
            conn = sqlite3.connect(self.db_path)
            val = json.dumps(value) if not isinstance(value, str) else value
            conn.execute('INSERT OR REPLACE INTO knowledge (category, key, value) VALUES (?,?,?)', (category, key, val))
            conn.commit(); conn.close()
            return ToolResult(True, {"stored": True})
        except Exception as e:
            return ToolResult(False, None, str(e))
    
    def retrieve(self, category: str, key: str = None) -> ToolResult:
        try:
            conn = sqlite3.connect(self.db_path)
            if key:
                row = conn.execute('SELECT value FROM knowledge WHERE category=? AND key=?', (category, key)).fetchone()
                conn.close()
                if row:
                    try: return ToolResult(True, json.loads(row[0]))
                    except: return ToolResult(True, row[0])
                return ToolResult(False, None, "Not found")
            else:
                rows = conn.execute('SELECT key, value FROM knowledge WHERE category=?', (category,)).fetchall()
                conn.close()
                return ToolResult(True, {r[0]: r[1] for r in rows})
        except Exception as e:
            return ToolResult(False, None, str(e))
    
    def search(self, query: str) -> ToolResult:
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute('SELECT category, key, value FROM knowledge WHERE key LIKE ? OR value LIKE ? LIMIT 20',
                (f'%{query}%', f'%{query}%')).fetchall()
            conn.close()
            return ToolResult(True, [{"category": r[0], "key": r[1], "value": r[2]} for r in rows])
        except Exception as e:
            return ToolResult(False, None, str(e))
    
    def log_task(self, task: str, result: str, success: bool) -> ToolResult:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('INSERT INTO tasks (task, result, success) VALUES (?,?,?)', (task, result, 1 if success else 0))
            conn.commit(); conn.close()
            return ToolResult(True, {"logged": True})
        except Exception as e:
            return ToolResult(False, None, str(e))
    
    def get_task_history(self, limit: int = 20) -> ToolResult:
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute('SELECT task, result, success, timestamp FROM tasks ORDER BY timestamp DESC LIMIT ?', (limit,)).fetchall()
            conn.close()
            return ToolResult(True, [{"task": r[0], "result": r[1], "success": bool(r[2]), "time": r[3]} for r in rows])
        except Exception as e:
            return ToolResult(False, None, str(e))
    
    def save_code(self, name: str, code: str, language: str = "python", desc: str = "") -> ToolResult:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('INSERT OR REPLACE INTO code_snippets (name, code, language, description) VALUES (?,?,?,?)',
                (name, code, language, desc))
            conn.commit(); conn.close()
            return ToolResult(True, {"saved": name})
        except Exception as e:
            return ToolResult(False, None, str(e))

class APICallerTool:
    """Make HTTP API calls."""
    name = "api_call"
    
    def execute(self, url: str, method: str = "GET", headers: Dict = None, 
                data: Dict = None, json_body: Dict = None) -> ToolResult:
        if not REQUESTS_OK:
            return ToolResult(False, None, "requests not installed")
        try:
            r = requests.request(method, url, headers=headers, data=data, json=json_body, timeout=30)
            try: resp_data = r.json()
            except: resp_data = r.text[:5000]
            return ToolResult(True, {"status": r.status_code, "data": resp_data})
        except Exception as e:
            return ToolResult(False, None, str(e))

class GitTool:
    """Git operations."""
    name = "git"
    
    def _run(self, path: str, args: List[str]) -> Tuple[bool, str]:
        try:
            r = subprocess.run(["git"] + args, cwd=path, capture_output=True, text=True, timeout=60)
            return (r.returncode == 0, r.stdout if r.returncode == 0 else r.stderr)
        except Exception as e:
            return (False, str(e))
    
    def execute(self, action: str, path: str = ".", **kw) -> ToolResult:
        if action == "status":
            ok, out = self._run(path, ["status", "--porcelain"])
            return ToolResult(ok, {"clean": len(out.strip()) == 0, "output": out})
        elif action == "log":
            ok, out = self._run(path, ["log", f"-{kw.get('num', 10)}", "--oneline"])
            return ToolResult(ok, out.strip().split("\n") if ok else None, None if ok else out)
        elif action == "add":
            ok, out = self._run(path, ["add", "-A"])
            return ToolResult(ok, {"added": True} if ok else None, None if ok else out)
        elif action == "commit":
            ok, out = self._run(path, ["commit", "-m", kw.get("message", "Nova auto-commit")])
            return ToolResult(ok, {"committed": True} if ok else None, None if ok else out)
        elif action == "push":
            ok, out = self._run(path, ["push"])
            return ToolResult(ok, {"pushed": True} if ok else None, None if ok else out)
        elif action == "pull":
            ok, out = self._run(path, ["pull"])
            return ToolResult(ok, out if ok else None, None if ok else out)
        return ToolResult(False, None, f"Unknown action: {action}")

class SystemMonitorTool:
    """Monitor system resources."""
    name = "system_monitor"
    
    def execute(self, action: str = "overview") -> ToolResult:
        if not PSUTIL_OK:
            return ToolResult(False, None, "psutil not installed")
        try:
            if action == "overview":
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                return ToolResult(True, {
                    "cpu_percent": psutil.cpu_percent(interval=1),
                    "memory_percent": mem.percent,
                    "memory_used_gb": mem.used // (1024**3),
                    "disk_percent": disk.percent
                })
            elif action == "processes":
                procs = []
                for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        info = p.info
                        if info.get('cpu_percent', 0) > 0:
                            procs.append(info)
                    except: pass
                procs.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
                return ToolResult(True, procs[:15])
            return ToolResult(False, None, f"Unknown action: {action}")
        except Exception as e:
            return ToolResult(False, None, str(e))

class ScreenshotTool:
    """Capture screenshots."""
    name = "screenshot"
    
    def execute(self, save_path: str = None) -> ToolResult:
        try:
            import pyautogui
            import io
            screenshot = pyautogui.screenshot()
            if save_path:
                screenshot.save(save_path)
                return ToolResult(True, {"path": save_path, "size": screenshot.size})
            buffer = io.BytesIO()
            screenshot.save(buffer, format='PNG')
            return ToolResult(True, {"base64": base64.b64encode(buffer.getvalue()).decode()[:100] + "...", "size": screenshot.size})
        except Exception as e:
            return ToolResult(False, None, str(e))

class AutomationExecutorTool:
    """Execute high-level automation commands via UCE."""
    name = "automation_executor"
    
    def execute(self, command: str) -> ToolResult:
        try:
            from nova_system.nova_automation import quick_command
            success, message = quick_command(command)
            return ToolResult(success, message)
        except Exception as e:
            return ToolResult(False, None, str(e))

# Tool Registry
class ToolRegistry:
    def __init__(self):
        self.tools = {}
        self._register_defaults()
    
    def _register_defaults(self):
        self.tools["web_search"] = WebSearchTool()
        self.tools["web_scraper"] = WebScraperTool()
        self.tools["knowledge_db"] = KnowledgeDB()
        self.tools["api_call"] = APICallerTool()
        self.tools["git"] = GitTool()
        self.tools["system_monitor"] = SystemMonitorTool()
        self.tools["screenshot"] = ScreenshotTool()
        self.tools["automation_executor"] = AutomationExecutorTool()
    
    def get(self, name: str): return self.tools.get(name)
    def list_tools(self): return list(self.tools.keys())
    def execute(self, name: str, **kw) -> ToolResult:
        tool = self.get(name)
        if not tool: return ToolResult(False, None, f"Tool not found: {name}")
        return tool.execute(**kw)

_registry = None
def get_tool_registry() -> ToolRegistry:
    global _registry
    if _registry is None: _registry = ToolRegistry()
    return _registry

if __name__ == "__main__":
    reg = get_tool_registry()
    print(f"Available tools: {reg.list_tools()}")
