#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Self-Programming Engine
==============================
Gives Nova the ability to:
1. Modify its own source code
2. Learn from past tasks and remember solutions
3. Decompose complex goals into sub-tasks
4. Train itself by analyzing successful patterns
"""

import os
import sys
import json
import hashlib
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

# Path to Nova's core files (for self-modification)
NOVA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MEMORY_FILE = os.path.join(NOVA_ROOT, "nova_system", "memory.json")
SKILLS_FILE = os.path.join(NOVA_ROOT, "nova_system", "skills.json")


class NovaMemory:
    """
    Persistent memory system for Nova.
    Stores: Task history, learned patterns, user preferences, successful code snippets.
    """
    
    def __init__(self):
        self.memory_path = MEMORY_FILE
        self.data = self._load()
    
    def _load(self) -> Dict:
        """Load memory from disk."""
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            "tasks": [],           # History of completed tasks
            "patterns": {},        # Learned patterns (task_type -> best_approach)
            "code_snippets": {},   # Successful code indexed by purpose
            "user_preferences": {},# User-specific preferences
            "training_data": []    # Data for self-improvement
        }
    
    def save(self):
        """Persist memory to disk."""
        try:
            os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
            with open(self.memory_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Memory save failed: {e}")
    
    def remember_task(self, task: str, result: str, success: bool, steps: List[Dict]):
        """Store a completed task for future learning."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "result": result,
            "success": success,
            "steps": steps,
            "hash": hashlib.md5(task.encode()).hexdigest()[:8]
        }
        self.data["tasks"].append(entry)
        
        # Keep only last 100 tasks
        self.data["tasks"] = self.data["tasks"][-100:]
        
        # If successful, extract patterns
        if success:
            self._extract_pattern(task, steps)
        
        self.save()
    
    def _extract_pattern(self, task: str, steps: List[Dict]):
        """Extract reusable patterns from successful tasks."""
        # Simple keyword-based categorization
        task_lower = task.lower()
        
        categories = {
            "file_operations": ["create file", "write file", "read file", "delete file", "modify"],
            "web_tasks": ["open browser", "search", "navigate", "download", "scrape"],
            "system_tasks": ["open app", "close app", "volume", "brightness", "lock", "shutdown"],
            "coding_tasks": ["program", "code", "script", "function", "class", "debug", "fix"],
            "self_modification": ["improve yourself", "upgrade", "train", "learn", "modify yourself"]
        }
        
        for category, keywords in categories.items():
            if any(kw in task_lower for kw in keywords):
                if category not in self.data["patterns"]:
                    self.data["patterns"][category] = []
                
                pattern = {
                    "task": task,
                    "steps": [s.get("action") for s in steps if isinstance(s, dict)],
                    "timestamp": datetime.now().isoformat()
                }
                self.data["patterns"][category].append(pattern)
                
                # Keep only last 10 patterns per category
                self.data["patterns"][category] = self.data["patterns"][category][-10:]
    
    def store_code_snippet(self, purpose: str, code: str):
        """Store a successful code snippet for reuse."""
        self.data["code_snippets"][purpose] = {
            "code": code,
            "timestamp": datetime.now().isoformat()
        }
        self.save()
    
    def find_similar_task(self, task: str) -> Optional[Dict]:
        """Find a similar past task to learn from."""
        task_words = set(task.lower().split())
        
        best_match = None
        best_score = 0
        
        for past_task in self.data["tasks"]:
            if not past_task.get("success"):
                continue
            
            past_words = set(past_task["task"].lower().split())
            overlap = len(task_words & past_words)
            
            if overlap > best_score:
                best_score = overlap
                best_match = past_task
        
        return best_match if best_score >= 2 else None
    
    def get_pattern_for_category(self, category: str) -> List[Dict]:
        """Get learned patterns for a task category."""
        return self.data["patterns"].get(category, [])


class NovaSkillLibrary:
    """
    Pre-built skills that Nova can use and extend.
    """
    
    def __init__(self):
        self.skills_path = SKILLS_FILE
        self.skills = self._load()
    
    def _load(self) -> Dict:
        """Load skills from disk."""
        if os.path.exists(self.skills_path):
            try:
                with open(self.skills_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Default skills
        return {
            "create_python_script": {
                "description": "Create a Python script file",
                "template": "def {function_name}():\n    \"\"\"Generated by Nova.\"\"\"\n    {body}\n\nif __name__ == '__main__':\n    {function_name}()"
            },
            "create_web_scraper": {
                "description": "Create a web scraper",
                "template": "import requests\nfrom bs4 import BeautifulSoup\n\ndef scrape(url):\n    response = requests.get(url)\n    soup = BeautifulSoup(response.text, 'html.parser')\n    return soup"
            },
            "create_automation_script": {
                "description": "Create a desktop automation script",
                "template": "import pyautogui\nimport time\n\ndef automate():\n    time.sleep(2)  # Setup time\n    {actions}\n\nif __name__ == '__main__':\n    automate()"
            }
        }
    
    def save(self):
        """Persist skills to disk."""
        try:
            os.makedirs(os.path.dirname(self.skills_path), exist_ok=True)
            with open(self.skills_path, 'w', encoding='utf-8') as f:
                json.dump(self.skills, f, indent=2)
        except Exception as e:
            print(f"⚠️ Skills save failed: {e}")
    
    def add_skill(self, name: str, description: str, template: str):
        """Add a new skill."""
        self.skills[name] = {
            "description": description,
            "template": template,
            "created": datetime.now().isoformat()
        }
        self.save()
    
    def get_skill(self, name: str) -> Optional[Dict]:
        """Get a skill by name."""
        return self.skills.get(name)
    
    def list_skills(self) -> List[str]:
        """List all available skills."""
        return list(self.skills.keys())


class SelfProgrammingEngine:
    """
    The core engine that allows Nova to modify its own code.
    """
    
    def __init__(self, brain=None):
        self.brain = brain
        self.memory = NovaMemory()
        self.skills = NovaSkillLibrary()
        self.nova_files = self._discover_nova_files()
    
    def _discover_nova_files(self) -> Dict[str, str]:
        """Discover all Nova source files."""
        files = {}
        for root, dirs, filenames in os.walk(NOVA_ROOT):
            # Skip hidden and cache directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__' and d != '.venv']
            
            for filename in filenames:
                if filename.endswith('.py'):
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, NOVA_ROOT)
                    files[rel_path] = full_path
        
        return files
    
    def read_own_source(self, filename: str) -> Optional[str]:
        """Read one of Nova's own source files."""
        # Security: Only allow reading Nova's own files
        if filename in self.nova_files:
            try:
                with open(self.nova_files[filename], 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return f"Error reading {filename}: {e}"
        
        # Try by basename
        for rel_path, full_path in self.nova_files.items():
            if filename in rel_path:
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    return f"Error reading {filename}: {e}"
        
        return f"File not found: {filename}"
    
    def modify_own_source(self, filename: str, new_content: str, backup: bool = True) -> tuple:
        """
        Modify one of Nova's own source files.
        CAUTION: This is powerful and potentially dangerous.
        """
        target_path = None
        
        # Find the file
        if filename in self.nova_files:
            target_path = self.nova_files[filename]
        else:
            for rel_path, full_path in self.nova_files.items():
                if filename in rel_path:
                    target_path = full_path
                    break
        
        if not target_path:
            return False, f"Cannot modify: {filename} not found"
        
        try:
            # Create backup
            if backup:
                backup_path = target_path + ".backup"
                with open(target_path, 'r', encoding='utf-8') as f:
                    original = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original)
            
            # Validate syntax before writing
            try:
                compile(new_content, filename, 'exec')
            except SyntaxError as e:
                return False, f"Syntax error in new code: {e}"
            
            # Write new content
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True, f"Successfully modified {filename}"
        
        except Exception as e:
            return False, f"Error modifying {filename}: {e}"
    
    def add_function_to_file(self, filename: str, function_code: str) -> tuple:
        """Add a new function to an existing file."""
        current_code = self.read_own_source(filename)
        
        if current_code.startswith("Error") or current_code.startswith("File not"):
            return False, current_code
        
        # Append the function
        new_code = current_code.rstrip() + "\n\n" + function_code + "\n"
        
        return self.modify_own_source(filename, new_code)
    
    def create_new_module(self, module_name: str, code: str) -> tuple:
        """Create a new Python module in Nova's system."""
        if not module_name.endswith('.py'):
            module_name += '.py'
        
        target_path = os.path.join(NOVA_ROOT, "nova_system", module_name)
        
        try:
            # Validate syntax
            compile(code, module_name, 'exec')
            
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Update discovered files
            self.nova_files[f"nova_system/{module_name}"] = target_path
            
            return True, f"Created new module: {module_name}"
        
        except SyntaxError as e:
            return False, f"Syntax error: {e}"
        except Exception as e:
            return False, f"Error creating module: {e}"
    
    def analyze_own_capabilities(self) -> Dict:
        """Analyze Nova's current capabilities by reading its source."""
        capabilities = {
            "files": list(self.nova_files.keys()),
            "classes": [],
            "functions": [],
            "skills": self.skills.list_skills(),
            "memory_stats": {
                "tasks_remembered": len(self.memory.data["tasks"]),
                "patterns_learned": len(self.memory.data["patterns"]),
                "code_snippets": len(self.memory.data["code_snippets"])
            }
        }
        
        # Quick analysis of main files
        important_files = ["interface/cli.py", "nova_system/nova_agent.py", "nova_system/nova_automation.py"]
        
        for filename in important_files:
            code = self.read_own_source(filename)
            if code and not code.startswith("Error"):
                # Count classes and functions
                for line in code.split('\n'):
                    stripped = line.strip()
                    if stripped.startswith('class '):
                        class_name = stripped.split('(')[0].replace('class ', '').strip(':')
                        capabilities["classes"].append(f"{filename}::{class_name}")
                    elif stripped.startswith('def '):
                        func_name = stripped.split('(')[0].replace('def ', '')
                        capabilities["functions"].append(f"{filename}::{func_name}")
        
        return capabilities
    
    def decompose_complex_task(self, task: str) -> List[Dict]:
        """
        Break down a complex task into smaller, executable steps.
        Uses LLM if available, otherwise uses pattern matching.
        """
        if self.brain and self.brain.available:
            # Use LLM to decompose
            prompt = f"""
            Break down this complex task into simple, executable steps.
            Each step should be ONE action that can be immediately executed.
            
            Task: {task}
            
            Output format (JSON list):
            [
                {{"step": 1, "action": "action_type", "description": "what to do", "params": {{}}}},
                ...
            ]
            
            Available actions:
            - execute_python: Run Python code
            - execute_command: Run terminal command
            - read_file: Read a file
            - write_file: Write to a file
            - modify_source: Modify Nova's own code
            - create_module: Create a new Python module
            - search_web: Search for information
            - chat: Communicate with user
            
            Return ONLY valid JSON.
            """
            
            response = self.brain.generate_response(prompt)
            
            try:
                # Clean and parse
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0]
                elif "```" in response:
                    response = response.split("```")[1].split("```")[0]
                
                start = response.find('[')
                end = response.rfind(']')
                if start != -1 and end != -1:
                    response = response[start:end+1]
                
                return json.loads(response)
            except:
                pass
        
        # Fallback: Simple rule-based decomposition
        steps = []
        task_lower = task.lower()
        
        if "create" in task_lower and "file" in task_lower:
            steps.append({"step": 1, "action": "write_file", "description": "Create the file"})
        
        if "modify" in task_lower or "change" in task_lower:
            steps.append({"step": 1, "action": "read_file", "description": "Read current content"})
            steps.append({"step": 2, "action": "modify_source", "description": "Apply changes"})
        
        if "program" in task_lower or "code" in task_lower:
            steps.append({"step": 1, "action": "execute_python", "description": "Write and run code"})
        
        if not steps:
            steps.append({"step": 1, "action": "chat", "description": "Clarify the task with user"})
        
        return steps
    
    def train_on_task(self, task: str, user_feedback: str, success: bool):
        """
        Learn from a completed task based on user feedback.
        """
        training_entry = {
            "timestamp": datetime.now().isoformat(),
            "task": task,
            "feedback": user_feedback,
            "success": success
        }
        
        self.memory.data["training_data"].append(training_entry)
        
        # Keep last 50 training entries
        self.memory.data["training_data"] = self.memory.data["training_data"][-50:]
        
        self.memory.save()
        
        # If this was a successful self-modification task, remember the pattern
        if success and "modify" in task.lower() and "self" in task.lower():
            self.memory.store_code_snippet(
                f"self_mod_{datetime.now().strftime('%Y%m%d_%H%M')}",
                task
            )
    
    def suggest_improvement(self) -> str:
        """
        Analyze past failures and suggest improvements.
        """
        failures = [t for t in self.memory.data["tasks"] if not t.get("success")]
        
        if not failures:
            return "No failures to analyze. System performing well!"
        
        # Categorize failures
        failure_types = {}
        for f in failures:
            task = f.get("task", "").lower()
            
            if "file" in task:
                failure_types["file_operations"] = failure_types.get("file_operations", 0) + 1
            elif "code" in task or "program" in task:
                failure_types["coding"] = failure_types.get("coding", 0) + 1
            else:
                failure_types["other"] = failure_types.get("other", 0) + 1
        
        most_failed = max(failure_types, key=failure_types.get) if failure_types else "unknown"
        
        suggestions = {
            "file_operations": "Consider improving file path handling and permissions checks.",
            "coding": "Add more validation for generated code before execution.",
            "other": "Expand the task decomposition rules for better coverage."
        }
        
        return suggestions.get(most_failed, "Continue learning from user feedback.")


# Global instance
_engine = None

def get_self_programming_engine(brain=None):
    """Get or create the self-programming engine."""
    global _engine
    if _engine is None:
        _engine = SelfProgrammingEngine(brain)
    elif brain and not _engine.brain:
        _engine.brain = brain
    return _engine
