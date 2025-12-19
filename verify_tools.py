
import os
import sys
# Add parent dir to path to import agent
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agent.enhanced_agent import ToolRegistry, FileTrieIndexerTool, DetailedStatusTool, ProcessManagerTool

def test_tools():
    registry = ToolRegistry()
    
    print("--- Testing DetailedStatusTool ---")
    status_tool = DetailedStatusTool()
    result = status_tool.execute({})
    print(f"Success: {result.success}")
    print(f"Output:\n{result.output}")
    
    print("\n--- Testing FileTrieIndexerTool ---")
    trie_tool = FileTrieIndexerTool()
    # Test Index
    result = trie_tool.execute({"action": "index", "prefix": ""})
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
