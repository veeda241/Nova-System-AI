# NOVA SYSTEM AI v2.0 - STRENGTH UPGRADE COMPLETE
# ================================================
# Run this file to see all new capabilities

import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def show_nova_capabilities():
    """Display all Nova v2.0 capabilities."""
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                       🚀 NOVA SYSTEM AI v2.0 - STRONGER THAN EVER            ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    # Check system status
    try:
        from nova_system import status
        s = status()
        print("📊 SYSTEM STATUS:")
        print(f"   Version: {s['version']}")
        print(f"   Enhanced Brain: {'✅' if s['enhanced_brain'] else '❌'}")
        print(f"   Enhanced Agent: {'✅' if s['enhanced_agent'] else '❌'}")
        print(f"   Advanced Tools: {'✅' if s['tools'] else '❌'}")
        print(f"   Self-Programming: {'✅' if s['self_programming'] else '❌'}")
        print(f"   Automation Engine: {'✅' if s['automation'] else '❌'}")
    except Exception as e:
        print(f"   Status check error: {e}")
    
    print("\n" + "="*70)
    
    # Brain capabilities
    print("\n🧠 ENHANCED BRAIN FEATURES:")
    print("   • Chain-of-Thought Reasoning - Thinks step-by-step for complex problems")
    print("   • Self-Reflection - Learns from errors and improves responses")
    print("   • Streaming Responses - Real-time output for faster interaction")
    print("   • Conversation Memory - Remembers context across turns")
    print("   • Stronger Personality - Confident, action-oriented, never says 'I can't'")
    print("   • Code Validation - Checks generated code for errors before running")
    
    # Check brain
    try:
        from nova_system.nova_enhanced_brain import get_enhanced_brain
        brain = get_enhanced_brain()
        if brain.available:
            print(f"\n   ✅ Brain Online: {brain.model}")
            print(f"   📈 Stats: {brain.stats['successful_requests']} successful requests")
        else:
            print("\n   ⚠️ Brain offline - start Ollama to enable")
    except:
        pass
    
    print("\n" + "="*70)
    
    # Tools
    print("\n🔧 NEW POWERFUL TOOLS:")
    try:
        from nova_system.nova_tools import get_tool_registry
        registry = get_tool_registry()
        tools = registry.list_tools()
        
        tool_descriptions = {
            "web_search": "Search the web using DuckDuckGo (no API key needed)",
            "web_scraper": "Scrape and extract content from any webpage",
            "knowledge_db": "Persistent SQLite database for storing knowledge",
            "api_call": "Make HTTP requests to external APIs",
            "git": "Git version control operations",
            "system_monitor": "Monitor CPU, memory, disk usage",
            "screenshot": "Capture screenshots of the screen"
        }
        
        for tool in tools:
            desc = tool_descriptions.get(tool, "Advanced tool")
            print(f"   • {tool}: {desc}")
    except Exception as e:
        print(f"   Tool loading error: {e}")
    
    print("\n" + "="*70)
    
    # Agent capabilities
    print("\n🤖 ENHANCED AGENT CAPABILITIES:")
    print("   • ReAct Loop - Reason + Act autonomously")
    print("   • Error Recovery - Reflects on mistakes and adjusts approach")
    print("   • Multi-step Planning - Breaks complex tasks into simple steps")
    print("   • Tool Chaining - Uses multiple tools together")
    print("   • Web Research - Can search and scrape web for information")
    print("   • Code Execution - Writes and runs Python/shell commands")
    print("   • Knowledge Persistence - Remembers information across sessions")
    
    print("\n" + "="*70)
    
    # Memory & Learning
    print("\n💾 MEMORY & LEARNING:")
    try:
        from nova_system.nova_tools import KnowledgeDB
        db = KnowledgeDB()
        # Test storage
        result = db.store("test", "upgrade_check", {"upgraded": True, "version": "2.0"})
        if result.success:
            print("   ✅ Knowledge Database: Active")
        
        # Get task history
        history = db.get_task_history(limit=5)
        if history.success and history.data:
            print(f"   📝 Tasks in history: {len(history.data)}")
    except Exception as e:
        print(f"   Database error: {e}")
    
    print("\n" + "="*70)
    
    # How to use
    print("""
📖 HOW TO USE NOVA v2.0:

1. INTERACTIVE MODE (recommended):
   python nova_cli.py
   
2. QUICK COMMANDS:
   python -c "from nova_system import quick_run; quick_run('your task here')"

3. ACCESS ENHANCED BRAIN:
   from nova_system.nova_enhanced_brain import get_enhanced_brain
   brain = get_enhanced_brain()
   response = brain.generate("Your question here")
   
4. USE TOOLS DIRECTLY:
   from nova_system.nova_tools import get_tool_registry
   tools = get_tool_registry()
   result = tools.execute('web_search', query='python tutorials')

5. RUN AUTONOMOUS AGENT:
   from nova_system.nova_enhanced_agent import get_enhanced_agent
   agent = get_enhanced_agent()
   result = agent.run_goal("Create a simple calculator app")

🎯 Nova is now STRONGER, SMARTER, and MORE CAPABLE than ever!
    """)


if __name__ == "__main__":
    show_nova_capabilities()
