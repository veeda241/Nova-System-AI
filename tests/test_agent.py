#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Tests - Agent Tests
========================
Unit tests for agent components.
"""

import os
import sys
import unittest

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestTools(unittest.TestCase):
    """Tests for MCP tools."""
    
    def test_import_tools(self):
        """Test that tools can be imported."""
        from agent.tools import TOOLS
        self.assertIsInstance(TOOLS, dict)
        self.assertGreater(len(TOOLS), 0)
    
    def test_create_python_file_tool(self):
        """Test CreatePythonFileTool."""
        from agent.tools import CreatePythonFileTool
        tool = CreatePythonFileTool()
        
        result = tool.execute(code="print('test')", filename="test_unit.py")
        self.assertTrue(result['success'])
        self.assertIn('filepath', result)
        
        # Cleanup
        if os.path.exists(result['filepath']):
            os.remove(result['filepath'])
    
    def test_execute_python_code_tool(self):
        """Test ExecutePythonCodeTool."""
        from agent.tools import ExecutePythonCodeTool
        tool = ExecutePythonCodeTool()
        
        result = tool.execute(code="print(2+2)")
        self.assertTrue(result['success'])
        self.assertIn('4', result['output'])
    
    def test_list_files_tool(self):
        """Test ListFilesTool."""
        from agent.tools import ListFilesTool
        tool = ListFilesTool()
        
        result = tool.execute()
        self.assertTrue(result['success'])
        self.assertIn('files', result)
    
    def test_safety_check(self):
        """Test code safety checker."""
        from agent.tools import check_code_safety
        
        # Safe code
        is_safe, _ = check_code_safety("print('hello')")
        self.assertTrue(is_safe)
        
        # Unsafe code
        is_safe, _ = check_code_safety("os.system('rm -rf /')")
        self.assertFalse(is_safe)


class TestPlanner(unittest.TestCase):
    """Tests for agent planner."""
    
    def test_import_planner(self):
        """Test that planner can be imported."""
        from agent.planner import Planner
        self.assertTrue(True)
    
    def test_create_plan(self):
        """Test plan creation."""
        from agent.planner import Planner
        planner = Planner()
        
        plan = planner.create_plan("Test goal", [
            {'description': 'Task 1', 'tool': 'list_files'},
            {'description': 'Task 2', 'tool': 'read_file'}
        ])
        
        self.assertEqual(plan.goal, "Test goal")
        self.assertEqual(len(plan.tasks), 2)
    
    def test_plan_summary(self):
        """Test plan summary generation."""
        from agent.planner import Planner
        planner = Planner()
        
        planner.create_plan("Test", [{'description': 'Test task'}])
        summary = planner.get_plan_summary()
        
        self.assertIn("Test", summary)


class TestExecutor(unittest.TestCase):
    """Tests for agent executor."""
    
    def test_import_executor(self):
        """Test that executor can be imported."""
        from agent.executor import Executor
        self.assertTrue(True)
    
    def test_get_available_tools(self):
        """Test getting available tools."""
        from agent.executor import Executor
        executor = Executor()
        
        tools = executor.get_available_tools()
        self.assertIn('create_python_file', tools)
        self.assertIn('execute_python_code', tools)
    
    def test_execute_single_tool(self):
        """Test executing a single tool."""
        from agent.executor import Executor
        executor = Executor()
        
        result = executor.execute_single('execute_python_code', code='print(1+1)')
        self.assertTrue(result.success)


class TestMCPAgent(unittest.TestCase):
    """Tests for MCP agent."""
    
    def test_import_agent(self):
        """Test that MCP agent can be imported."""
        from agent.claude_mcp_agent import ClaudeMCPAgent
        self.assertTrue(True)
    
    def test_agent_init(self):
        """Test agent initialization."""
        from agent.claude_mcp_agent import ClaudeMCPAgent
        agent = ClaudeMCPAgent()
        
        self.assertIsNotNone(agent.model)
        self.assertIsNotNone(agent.tools)
    
    def test_agent_tools(self):
        """Test agent has required tools."""
        from agent.claude_mcp_agent import ClaudeMCPAgent
        agent = ClaudeMCPAgent()
        
        self.assertIn('create_python_file', agent.tools)
        self.assertIn('execute_python_file', agent.tools)


if __name__ == '__main__':
    unittest.main(verbosity=2)
