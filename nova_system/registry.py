#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Registry - Model and Component Registry
=============================================
Central registry for managing AI models, tools, and components.
"""

import os
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ModelInfo:
    """Information about a registered model."""
    name: str
    type: str  # 'ollama', 'groq', 'gemini', 'local'
    version: str
    path: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    registered_at: str = ""
    
    def __post_init__(self):
        if not self.registered_at:
            self.registered_at = datetime.now().isoformat()


@dataclass  
class ToolInfo:
    """Information about a registered tool."""
    name: str
    description: str
    module: str
    class_name: str
    enabled: bool = True


class NovaRegistry:
    """Central registry for NOVA components."""
    
    def __init__(self, registry_file: str = None):
        self.registry_file = registry_file or os.path.join(
            os.path.dirname(__file__), "..", "data", "registry.json"
        )
        self.models: Dict[str, ModelInfo] = {}
        self.tools: Dict[str, ToolInfo] = {}
        self._load()
    
    def _load(self):
        """Load registry from file."""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r') as f:
                    data = json.load(f)
                    for name, info in data.get('models', {}).items():
                        self.models[name] = ModelInfo(**info)
                    for name, info in data.get('tools', {}).items():
                        self.tools[name] = ToolInfo(**info)
            except Exception as e:
                print(f"Warning: Could not load registry: {e}")
    
    def _save(self):
        """Save registry to file."""
        os.makedirs(os.path.dirname(self.registry_file), exist_ok=True)
        data = {
            'models': {name: asdict(info) for name, info in self.models.items()},
            'tools': {name: asdict(info) for name, info in self.tools.items()}
        }
        with open(self.registry_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    # Model Registry
    def register_model(self, name: str, model_type: str, version: str = "1.0", 
                       path: str = None, config: Dict = None) -> ModelInfo:
        """Register a new model."""
        model = ModelInfo(name=name, type=model_type, version=version, 
                          path=path, config=config)
        self.models[name] = model
        self._save()
        return model
    
    def get_model(self, name: str) -> Optional[ModelInfo]:
        """Get a registered model."""
        return self.models.get(name)
    
    def list_models(self, model_type: str = None) -> List[ModelInfo]:
        """List all registered models."""
        if model_type:
            return [m for m in self.models.values() if m.type == model_type]
        return list(self.models.values())
    
    def unregister_model(self, name: str) -> bool:
        """Unregister a model."""
        if name in self.models:
            del self.models[name]
            self._save()
            return True
        return False
    
    # Tool Registry
    def register_tool(self, name: str, description: str, module: str, 
                      class_name: str, enabled: bool = True) -> ToolInfo:
        """Register a new tool."""
        tool = ToolInfo(name=name, description=description, module=module,
                        class_name=class_name, enabled=enabled)
        self.tools[name] = tool
        self._save()
        return tool
    
    def get_tool(self, name: str) -> Optional[ToolInfo]:
        """Get a registered tool."""
        return self.tools.get(name)
    
    def list_tools(self, enabled_only: bool = True) -> List[ToolInfo]:
        """List all registered tools."""
        if enabled_only:
            return [t for t in self.tools.values() if t.enabled]
        return list(self.tools.values())
    
    def enable_tool(self, name: str, enabled: bool = True) -> bool:
        """Enable or disable a tool."""
        if name in self.tools:
            self.tools[name].enabled = enabled
            self._save()
            return True
        return False


# Global registry instance
_registry = None

def get_registry() -> NovaRegistry:
    """Get the global registry instance."""
    global _registry
    if _registry is None:
        _registry = NovaRegistry()
    return _registry


# Auto-register default components
def register_defaults():
    """Register default models and tools."""
    registry = get_registry()
    
    # Register default models
    if 'nova' not in registry.models:
        registry.register_model('nova', 'ollama', '1.0', 
                                config={'context_length': 8192})
    if 'qwen2.5-coder' not in registry.models:
        registry.register_model('qwen2.5-coder', 'ollama', '1.0')
    
    # Register default tools
    default_tools = [
        ('create_python_file', 'Create Python files', 'agent.tools', 'CreatePythonFileTool'),
        ('execute_python_file', 'Execute Python files', 'agent.tools', 'ExecutePythonFileTool'),
        ('execute_python_code', 'Execute Python code', 'agent.tools', 'ExecutePythonCodeTool'),
        ('read_file', 'Read file contents', 'agent.tools', 'ReadFileTool'),
        ('list_files', 'List files', 'agent.tools', 'ListFilesTool'),
        ('search_files', 'Search files', 'agent.tools', 'SearchFilesTool'),
    ]
    
    for name, desc, module, cls in default_tools:
        if name not in registry.tools:
            registry.register_tool(name, desc, module, cls)


if __name__ == "__main__":
    register_defaults()
    registry = get_registry()
    print("Models:", [m.name for m in registry.list_models()])
    print("Tools:", [t.name for t in registry.list_tools()])
