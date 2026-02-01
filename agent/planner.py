#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Agent Planner - Task Planning and Decomposition
=====================================================
Breaks down complex tasks into actionable steps.
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Task:
    """Represents a single task in the plan."""
    id: int
    description: str
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d['status'] = self.status.value
        return d


@dataclass
class Plan:
    """Represents a complete execution plan."""
    goal: str
    tasks: List[Task]
    current_task_idx: int = 0
    
    @property
    def current_task(self) -> Optional[Task]:
        if 0 <= self.current_task_idx < len(self.tasks):
            return self.tasks[self.current_task_idx]
        return None
    
    @property
    def is_complete(self) -> bool:
        return all(t.status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED] 
                   for t in self.tasks)
    
    @property
    def has_failed(self) -> bool:
        return any(t.status == TaskStatus.FAILED for t in self.tasks)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'goal': self.goal,
            'tasks': [t.to_dict() for t in self.tasks],
            'current_task_idx': self.current_task_idx
        }


class Planner:
    """Plans and decomposes tasks for the agent."""
    
    # Common task patterns
    TASK_PATTERNS = {
        'create_and_run': [
            {'tool': 'create_python_file', 'desc': 'Create the Python file'},
            {'tool': 'execute_python_file', 'desc': 'Execute the file'}
        ],
        'read_and_modify': [
            {'tool': 'read_file', 'desc': 'Read the file contents'},
            {'tool': 'create_python_file', 'desc': 'Create modified version'}
        ],
        'search_and_read': [
            {'tool': 'search_files', 'desc': 'Search for matching files'},
            {'tool': 'read_file', 'desc': 'Read the found file'}
        ]
    }
    
    def __init__(self):
        self.current_plan: Optional[Plan] = None
    
    def create_plan(self, goal: str, tasks: List[Dict[str, Any]]) -> Plan:
        """Create a new execution plan."""
        task_list = []
        for i, task in enumerate(tasks):
            task_list.append(Task(
                id=i + 1,
                description=task.get('description', f'Task {i+1}'),
                tool=task.get('tool'),
                args=task.get('args')
            ))
        
        self.current_plan = Plan(goal=goal, tasks=task_list)
        return self.current_plan
    
    def plan_from_pattern(self, goal: str, pattern: str, 
                          args_list: List[Dict[str, Any]]) -> Optional[Plan]:
        """Create a plan from a predefined pattern."""
        if pattern not in self.TASK_PATTERNS:
            return None
        
        template = self.TASK_PATTERNS[pattern]
        tasks = []
        
        for i, (tmpl, args) in enumerate(zip(template, args_list)):
            tasks.append({
                'description': tmpl['desc'],
                'tool': tmpl['tool'],
                'args': args
            })
        
        return self.create_plan(goal, tasks)
    
    def suggest_plan(self, query: str) -> Optional[Plan]:
        """Suggest a plan based on natural language query."""
        query_lower = query.lower()
        
        # Pattern matching for common requests
        if 'create' in query_lower and 'run' in query_lower:
            # Create and run pattern
            return self.create_plan(query, [
                {'description': 'Create the file', 'tool': 'create_python_file'},
                {'description': 'Execute the file', 'tool': 'execute_python_file'}
            ])
        
        elif 'read' in query_lower or 'show' in query_lower:
            return self.create_plan(query, [
                {'description': 'Read the file', 'tool': 'read_file'}
            ])
        
        elif 'list' in query_lower or 'find' in query_lower:
            return self.create_plan(query, [
                {'description': 'Search for files', 'tool': 'search_files'}
            ])
        
        elif 'calculate' in query_lower or 'compute' in query_lower:
            return self.create_plan(query, [
                {'description': 'Execute calculation', 'tool': 'execute_python_code'}
            ])
        
        return None
    
    def update_task_status(self, task_id: int, status: TaskStatus, 
                           result: str = None, error: str = None):
        """Update the status of a task."""
        if self.current_plan:
            for task in self.current_plan.tasks:
                if task.id == task_id:
                    task.status = status
                    task.result = result
                    task.error = error
                    break
    
    def advance_to_next_task(self) -> Optional[Task]:
        """Move to the next pending task."""
        if self.current_plan:
            for i, task in enumerate(self.current_plan.tasks):
                if task.status == TaskStatus.PENDING:
                    self.current_plan.current_task_idx = i
                    task.status = TaskStatus.IN_PROGRESS
                    return task
        return None
    
    def get_plan_summary(self) -> str:
        """Get a human-readable summary of the current plan."""
        if not self.current_plan:
            return "No active plan"
        
        lines = [f"📋 Plan: {self.current_plan.goal}", ""]
        
        for task in self.current_plan.tasks:
            if task.status == TaskStatus.COMPLETED:
                icon = "✅"
            elif task.status == TaskStatus.IN_PROGRESS:
                icon = "🔄"
            elif task.status == TaskStatus.FAILED:
                icon = "❌"
            elif task.status == TaskStatus.SKIPPED:
                icon = "⏭️"
            else:
                icon = "⬜"
            
            lines.append(f"  {icon} {task.id}. {task.description}")
            if task.tool:
                lines.append(f"      Tool: {task.tool}")
        
        return "\n".join(lines)


if __name__ == "__main__":
    planner = Planner()
    
    # Test plan creation
    plan = planner.create_plan(
        "Create and run hello world",
        [
            {'description': 'Create hello.py', 'tool': 'create_python_file', 
             'args': {'code': 'print("Hello!")', 'filename': 'hello.py'}},
            {'description': 'Run hello.py', 'tool': 'execute_python_file',
             'args': {'filepath': 'hello.py'}}
        ]
    )
    
    print(planner.get_plan_summary())
