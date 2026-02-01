
import os
import sys
# Add parent dir to path to import agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.tools import (
    CreatePythonFileTool,
    ExecutePythonFileTool,
    ReadFileTool,
    ListFilesTool
)

def test_tools():
    print("--- Testing MCP Tools ---")
    
    print("\n--- Testing ListFilesTool ---")
    list_tool = ListFilesTool()
    result = list_tool.execute()
    print(f"Success: {result.success}")
    print(f"Output:\n{result.output[:200]}...")
    print(f"Index Success: {result.success}")
    
    # Test Search
    result = trie_tool.execute({"action": "search", "prefix": "nova"})
    print(f"Search Success: {result.success}")
    print(f"Output:\n{result.output}")
    
    print("\n--- Testing ProcessManagerTool ---")
    proc_tool = ProcessManagerTool()
    result = proc_tool.execute({"action": "list"})
    print(f"List Success: {result.success}")
    print(f"Output:\n{result.output}")

if __name__ == "__main__":
    test_tools()
