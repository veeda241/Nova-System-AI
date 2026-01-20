#!/usr/bin/env python3
"""
NOVA SYSTEM - Enhanced AI Package
==================================
All Nova components for powerful autonomous AI operations.
Supports: Ollama, Groq, Gemini, OpenAI (auto-selects best available)
"""

# Multi-Model Brain (NEW) - Auto-selects best AI backend
try:
    from .multi_model_brain import MultiModelBrain, NovaBrain
    MULTI_MODEL_AVAILABLE = True
except ImportError:
    MultiModelBrain = None
    MULTI_MODEL_AVAILABLE = False

# Core Brain - Enhanced with CoT and Reflection
try:
    from .nova_enhanced_brain import EnhancedNovaBrain, get_enhanced_brain
except ImportError:
    EnhancedNovaBrain = None
    get_enhanced_brain = None

# Legacy Brain (fallback)
if not MULTI_MODEL_AVAILABLE:
    try:
        from .nova_ollama import NovaBrain
    except ImportError:
        NovaBrain = None

# Enhanced Agent
try:
    from .nova_enhanced_agent import EnhancedNovaAgent, get_enhanced_agent
except ImportError:
    EnhancedNovaAgent = None
    get_enhanced_agent = None

# Legacy Agent
try:
    from .nova_agent import NovaAutonomousAgent
except ImportError:
    NovaAutonomousAgent = None

# Advanced Tools
try:
    from .nova_tools import (
        get_tool_registry, ToolRegistry, ToolResult,
        WebSearchTool, WebScraperTool, KnowledgeDB,
        APICallerTool, GitTool, SystemMonitorTool, ScreenshotTool
    )
except ImportError:
    get_tool_registry = None

# Self-Programming Engine
try:
    from .self_programming import (
        SelfProgrammingEngine, get_self_programming_engine,
        NovaMemory, NovaSkillLibrary
    )
except ImportError:
    SelfProgrammingEngine = None
    get_self_programming_engine = None

# Automation Engines
try:
    from .nova_automation import (
        UnifiedControlEngine, HumanActionSimulator as HASE,
        AppControlLayer as AWCL_APP, WebControlLayer as AWCL_WEB,
        SystemInteractionEngine as SYSTEM
    )
except ImportError:
    UnifiedControlEngine = None
    HASE = None

# Version
__version__ = "2.0.0"
__author__ = "Nova System AI"

# Quick access functions
def get_nova():
    """Get the best available Nova agent."""
    if get_enhanced_agent:
        return get_enhanced_agent()
    elif NovaAutonomousAgent and NovaBrain:
        return NovaAutonomousAgent(NovaBrain())
    return None

def get_brain():
    """Get the best available Nova brain."""
    if get_enhanced_brain:
        return get_enhanced_brain()
    elif NovaBrain:
        return NovaBrain()
    return None

def quick_run(goal: str):
    """Quickly run a goal with Nova."""
    agent = get_nova()
    if agent:
        return agent.run_goal(goal)
    return {"error": "No agent available"}

# Status function
def status():
    """Get Nova system status."""
    return {
        "version": __version__,
        "enhanced_brain": EnhancedNovaBrain is not None,
        "enhanced_agent": EnhancedNovaAgent is not None,
        "tools": get_tool_registry is not None,
        "self_programming": SelfProgrammingEngine is not None,
        "automation": UnifiedControlEngine is not None
    }
