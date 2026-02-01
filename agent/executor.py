#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Agent Executor - Task Execution Engine
============================================
Executes planned tasks using available tools.
"""

import os
import sys
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools import TOOLS, execute_tool
from agent.planner import Planner, Plan, Task, TaskStatus


@dataclass
class ExecutionResult:
    """Result of task execution."""
    success: bool
    output: str
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


class Executor:
    """Executes tasks from a plan."""
    
    def __init__(self, planner: Planner = None):
        self.planner = planner or Planner()
        self.execution_history: list = []
        self.on_task_start: Optional[Callable[[Task], None]] = None
        self.on_task_complete: Optional[Callable[[Task, ExecutionResult], None]] = None
    
    def execute_tool(self, tool_name: str, args: Dict[str, Any]) -> ExecutionResult:
        """Execute a single tool."""
        if tool_name not in TOOLS:
            return ExecutionResult(
                success=False,
                output="",
                error=f"Unknown tool: {tool_name}"
            )
        
        try:
            result = execute_tool(tool_name, **args)
            
            success = result.get('success', False)
            
            # Format output
            if success:
                output_parts = []
                for key, value in result.items():
                    if key != 'success':
                        output_parts.append(f"{key}: {value}")
                output = ", ".join(output_parts)
            else:
                output = result.get('error', 'Unknown error')
            
            return ExecutionResult(
                success=success,
                output=output,
                error=result.get('error'),
                data=result
            )
            
        except Exception as e:
            return ExecutionResult(
                success=False,
                output="",
                error=str(e)
            )
    
    def execute_task(self, task: Task) -> ExecutionResult:
        """Execute a single task."""
        if self.on_task_start:
            self.on_task_start(task)
        
        if not task.tool:
            return ExecutionResult(
                success=False,
                output="",
                error="No tool specified for task"
            )
        
        args = task.args or {}
        result = self.execute_tool(task.tool, args)
        
        # Update task status
        if result.success:
            self.planner.update_task_status(
                task.id, TaskStatus.COMPLETED, result=result.output
            )
        else:
            self.planner.update_task_status(
                task.id, TaskStatus.FAILED, error=result.error
            )
        
        # Record in history
        self.execution_history.append({
            'task_id': task.id,
            'tool': task.tool,
            'args': args,
            'result': result
        })
        
        if self.on_task_complete:
            self.on_task_complete(task, result)
        
        return result
    
    def execute_plan(self, plan: Plan = None, stop_on_error: bool = True) -> bool:
        """Execute all tasks in a plan."""
        plan = plan or self.planner.current_plan
        
        if not plan:
            print("❌ No plan to execute")
            return False
        
        print(f"\n🚀 Executing plan: {plan.goal}\n")
        
        while not plan.is_complete:
            task = self.planner.advance_to_next_task()
            
            if not task:
                break
            
            print(f"[{task.id}/{len(plan.tasks)}] {task.description}")
            print(f"    Tool: {task.tool}")
            
            result = self.execute_task(task)
            
            if result.success:
                print(f"    ✅ Success: {result.output[:100]}...")
            else:
                print(f"    ❌ Failed: {result.error}")
                if stop_on_error:
                    return False
        
        if plan.has_failed:
            print(f"\n❌ Plan failed")
            return False
        else:
            print(f"\n✅ Plan completed successfully")
            return True
    
    def execute_single(self, tool_name: str, **kwargs) -> ExecutionResult:
        """Execute a single tool without a plan."""
        return self.execute_tool(tool_name, kwargs)
    
    def get_available_tools(self) -> list:
        """Get list of available tool names."""
        return list(TOOLS.keys())
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, str]]:
        """Get information about a specific tool."""
        tool = TOOLS.get(tool_name)
        if tool:
            return {
                'name': tool.name,
                'description': tool.description
            }
        return None


class AgentLoop:
    """Main agent execution loop combining planning and execution."""
    
    def __init__(self):
        self.planner = Planner()
        self.executor = Executor(self.planner)
    
    def run(self, goal: str, tasks: list) -> bool:
        """Run the agent with a goal and list of tasks."""
        # Create plan
        plan = self.planner.create_plan(goal, tasks)
        print(self.planner.get_plan_summary())
        
        # Execute plan
        return self.executor.execute_plan(plan)
    
    def run_interactive(self):
        """Run in interactive mode."""
        print("\n🤖 NOVA Agent - Interactive Mode")
        print("Type 'help' for commands, 'exit' to quit\n")
        
        while True:
            try:
                cmd = input("agent> ").strip()
                
                if not cmd:
                    continue
                
                if cmd.lower() == 'exit':
                    break
                
                if cmd.lower() == 'help':
                    print("\nCommands:")
                    print("  tools        - List available tools")
                    print("  exec <tool>  - Execute a tool")
                    print("  plan         - Show current plan")
                    print("  exit         - Exit agent")
                    continue
                
                if cmd.lower() == 'tools':
                    print("\nAvailable tools:")
                    for name in self.executor.get_available_tools():
                        info = self.executor.get_tool_info(name)
                        print(f"  {name}: {info['description']}")
                    continue
                
                if cmd.lower() == 'plan':
                    print(self.planner.get_plan_summary())
                    continue
                
                if cmd.startswith('exec '):
                    parts = cmd[5:].split(' ', 1)
                    tool_name = parts[0]
                    # Simple arg parsing for demo
                    result = self.executor.execute_single(tool_name)
                    print(f"Result: {result.output if result.success else result.error}")
                    continue
                
                print(f"Unknown command: {cmd}")
                
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")


if __name__ == "__main__":
    # Test executor
    agent = AgentLoop()
    
    # Simple test
    success = agent.run(
        "Test file creation and execution",
        [
            {
                'description': 'Create a test file',
                'tool': 'create_python_file',
                'args': {'code': 'print("Hello from Executor!")', 'filename': 'test_exec.py'}
            },
            {
                'description': 'Execute the test file',
                'tool': 'execute_python_file', 
                'args': {'filepath': 'workspace/test_exec.py'}
            }
        ]
    )
    
    print(f"\nFinal result: {'Success' if success else 'Failed'}")
