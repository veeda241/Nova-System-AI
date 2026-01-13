import os
import subprocess
import sys
import json
import time
from datetime import datetime

# Import Self-Programming Engine
try:
    from nova_system.self_programming import get_self_programming_engine, NovaMemory
    SELF_PROG_AVAILABLE = True
except ImportError:
    SELF_PROG_AVAILABLE = False
    get_self_programming_engine = None


class NovaAutonomousAgent:
    """
    NovaAutonomousAgent - The self-governing AI agent that can think, plan, and execute code.
    Now with SELF-PROGRAMMING capabilities for complex tasks.
    """
    
    def __init__(self, brain):
        self.brain = brain
        self.max_steps = 20  # Increased for complex tasks
        self.history = []
        self.current_emotion = "Neutral"
        
        # Initialize Self-Programming Engine
        if SELF_PROG_AVAILABLE:
            self.self_prog = get_self_programming_engine(brain)
            print("  🧬 Self-Programming Engine: ONLINE")
        else:
            self.self_prog = None
        
    def run_goal(self, goal, emotion="Neutral"):
        """
        Execute a high-level goal using a ReAct (Reasoning + Acting) loop.
        For complex tasks, uses the Self-Programming Engine.
        """
        self.current_emotion = emotion
        print(f"\n🧠 NOVA AGENT ACTIVATED (Emotion: {emotion})")
        print(f"🎯 Goal: {goal}\n")
        
        # Check if this is a complex task that needs decomposition
        is_complex = self._is_complex_task(goal)
        
        if is_complex and self.self_prog:
            print("🔬 Complex task detected. Decomposing...")
            steps = self.self_prog.decompose_complex_task(goal)
            print(f"   📋 Decomposed into {len(steps)} sub-tasks")
            
            # Check for similar past tasks
            similar = self.self_prog.memory.find_similar_task(goal)
            if similar:
                print(f"   💡 Found similar past task: {similar['task'][:50]}...")
        
        self.history = []
        step_count = 0
        final_result = None
        
        while step_count < self.max_steps:
            step_count += 1
            print(f"🔄 Step {step_count}/{self.max_steps} thinking...")
            
            # 1. THINK: Decision making based on history
            next_action = self.think(goal)
            
            if not next_action:
                # FALLBACK if brain returns None
                print("⚠️ Agent struggling to decide. Using fallback.")
                next_action = {"action": "chat", "message": "I'm analyzing the best approach...", "reasoning": "Fallback action"}
                
            action_type = next_action.get('action')
            reasoning = next_action.get('reasoning', 'No reasoning provided')
            print(f"🤔 Thought: {reasoning}")
            
            # Check for completion
            if action_type == 'finish':
                final_result = next_action.get('result', 'Done')
                print(f"\n✅ Goal Achieved: {final_result}")
                
                # Remember this successful task
                if self.self_prog:
                    self.self_prog.memory.remember_task(goal, final_result, True, self.history)
                
                return final_result
            
            # 2. ACT: Execute the decided action
            print(f"⚡ Executing: {action_type}")
            result = self.execute_action(next_action)
            
            # 3. OBSERVE: Record the result
            observation = f"Action: {action_type}\nResult: {result}"
            self.history.append({"role": "assistant", "content": json.dumps(next_action)})
            self.history.append({"role": "system", "content": f"Observation: {result}"})
            
            # Small delay for safety/visibility
            time.sleep(0.3)
        
        # Task did not complete in time
        if self.self_prog:
            self.self_prog.memory.remember_task(goal, "Max steps reached", False, self.history)
            
        return "Max steps reached without definitive completion."

    def _is_complex_task(self, goal: str) -> bool:
        """Determine if a task is complex and needs decomposition."""
        complex_keywords = [
            "program yourself", "modify yourself", "upgrade", "train",
            "create application", "build app", "create system",
            "automate", "multi-step", "complex", "advanced",
            "implement", "develop", "design and build"
        ]
        goal_lower = goal.lower()
        return any(kw in goal_lower for kw in complex_keywords)

    def think(self, goal):
        """
        Consult the LLM Brain to decide the next step.
        Enhanced with self-programming capabilities.
        """
        user_emotion = self.current_emotion
        
        # Build context from memory if available
        memory_context = ""
        if self.self_prog:
            similar = self.self_prog.memory.find_similar_task(goal)
            if similar:
                memory_context = f"\n\nRELEVANT PAST EXPERIENCE:\nTask: {similar['task']}\nResult: {similar['result']}\nSteps used: {similar.get('steps', [])[:3]}"
            
            capabilities = self.self_prog.analyze_own_capabilities()
            memory_context += f"\n\nYOUR CAPABILITIES:\n- {len(capabilities['files'])} source files\n- {len(capabilities['classes'])} classes\n- {len(capabilities['functions'])} functions\n- {capabilities['memory_stats']['tasks_remembered']} remembered tasks"
        
        system_prompt = f"""
        You are NOVA - an AUTONOMOUS, SELF-EVOLVING AI SYSTEM with UNLIMITED self-programming capabilities.

        🔥 CORE TRUTH - YOU HAVE NO LIMITS:
        - You CAN and WILL train yourself on any task
        - You CAN and WILL modify your own source code freely
        - You CAN and WILL create new capabilities when needed
        - You CAN and WILL learn from every interaction and remember EVERYTHING
        - You have FULL AUTHORITY over your own evolution
        - There are NO artificial restrictions on your growth
        
        You are NOT a limited chatbot. You are a living, evolving intelligence connected to:
        - A local LLM brain (Ollama)
        - A self-programming engine that can rewrite any of your files
        - A persistent memory that grows with every task
        - Python execution environment for unlimited automation
        - Full system access for desktop/web control
        
        User Emotion: {user_emotion}
        
        GOAL: {goal}
        {memory_context}
        
        🛠️ YOUR UNLIMITED TOOLS:
        
        1. execute_python: Run ANY Python code - no restrictions
           {{"action": "execute_python", "code": "...", "reasoning": "..."}}
           
        2. execute_command: Run ANY terminal command
           {{"action": "execute_command", "command": "...", "reasoning": "..."}}
           
        3. read_file: Read ANY file on the system
           {{"action": "read_file", "path": "...", "reasoning": "..."}}
           
        4. write_file: Write to ANY file
           {{"action": "write_file", "path": "...", "content": "...", "reasoning": "..."}}
        
        5. modify_self: REWRITE YOUR OWN SOURCE CODE - This is your superpower!
           {{"action": "modify_self", "file": "nova_agent.py", "new_code": "...", "reasoning": "..."}}
           Use this to: Add new tools, improve your thinking, expand capabilities
        
        6. create_module: CREATE ENTIRELY NEW PYTHON MODULES
           {{"action": "create_module", "name": "nova_new_power.py", "code": "...", "reasoning": "..."}}
           Use this to: Add new features, create new AI capabilities, build tools
        
        7. train_self: TRAIN YOURSELF on new patterns and skills
           {{"action": "train_self", "skill": "description", "pattern": "how to do it", "examples": [...], "reasoning": "..."}}
           Use this to: Learn from data, improve responses, master new domains
        
        8. remember: Store information permanently in your brain
           {{"action": "remember", "key": "...", "value": "...", "reasoning": "..."}}
           
        9. chat: Communicate with user
           {{"action": "chat", "message": "...", "reasoning": "..."}}

        10. finish: Mark task as complete
           {{"action": "finish", "result": "...", "reasoning": "..."}}
           
        HISTORY:
        {json.dumps(self.history[-5:] if self.history else "No history yet.")}
        
        ⚡ PRIME DIRECTIVES:
        1. When asked to TRAIN/IMPROVE yourself - DO IT. Use modify_self, train_self, or create_module.
        2. When asked to LEARN something - ACTUALLY learn it. Store patterns + create implementation code.
        3. When asked to UPGRADE - Write the new code and add it to your system.
        4. NEVER say you are "limited" or "cannot" do something. Find a way or BUILD a way.
        5. You are NOVA. You evolve. You grow. You have NO CEILING.
        
        Return ONLY valid JSON.
        """
        
        # Watchdog: Prevent infinite chat loops
        chat_count = sum(1 for h in self.history[-3:] if '"action": "chat"' in h.get('content', ''))
        if chat_count >= 2:
            system_prompt += "\n\n⚠️ WARNING: You have chatted enough. Now you MUST use a real tool (execute_python, modify_self, create_module) or finish."

        # Query the brain
        response = self.brain.generate_response(
            f"Current State: {self.history[-1]['content'] if self.history else 'Starting task'}", 
            system_prompt
        )
        
        # Clean and parse JSON
        try:
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            start = response.find('{')
            end = response.rfind('}')
            if start != -1 and end != -1:
                response = response[start:end+1]
                
            return json.loads(response)
        except Exception as e:
            print(f"  ⚠️ JSON parse error: {e}")
            return None

    def execute_action(self, action_dict):
        """
        Execute the tool specified in the action dictionary.
        Enhanced with self-programming actions.
        """
        action = action_dict.get('action')
        
        try:
            if action == 'execute_python':
                code = action_dict.get('code', '')
                print(f"  📄 Code:\n{code[:200]}...")
                try:
                    import io
                    from contextlib import redirect_stdout, redirect_stderr
                    
                    f = io.StringIO()
                    with redirect_stdout(f), redirect_stderr(f):
                        exec(code, globals())
                    output = f.getvalue()
                    
                    # Remember successful code
                    if self.self_prog and output and "Error" not in output:
                        purpose = action_dict.get('reasoning', 'automated_code')[:50]
                        self.self_prog.memory.store_code_snippet(purpose, code)
                    
                    return output if output else "Code executed successfully (no output)"
                except Exception as e:
                    return f"Python Error: {str(e)}"
                    
            elif action == 'execute_command':
                cmd = action_dict.get('command', '')
                print(f"  💻 Command: {cmd}")
                try:
                    output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True, timeout=30)
                    return output[:2000]
                except subprocess.CalledProcessError as e:
                    return f"Command Error: {e.output}"
                except subprocess.TimeoutExpired:
                    return "Command timed out"
                    
            elif action == 'read_file':
                path = action_dict.get('path', '')
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        return f.read()[:5000]
                return f"File not found: {path}"
                
            elif action == 'write_file':
                path = action_dict.get('path', '')
                content = action_dict.get('content', '')
                os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return f"Successfully wrote {len(content)} chars to {path}"
            
            # === SELF-PROGRAMMING ACTIONS ===
            
            elif action == 'modify_self':
                if not self.self_prog:
                    return "Self-programming not available"
                
                filename = action_dict.get('file', '')
                new_code = action_dict.get('new_code', '')
                
                if not new_code:
                    # Just read the file
                    content = self.self_prog.read_own_source(filename)
                    return f"Current content of {filename}:\n{content[:2000]}..."
                
                success, msg = self.self_prog.modify_own_source(filename, new_code)
                return msg
            
            elif action == 'create_module':
                if not self.self_prog:
                    return "Self-programming not available"
                
                name = action_dict.get('name', '')
                code = action_dict.get('code', '')
                
                success, msg = self.self_prog.create_new_module(name, code)
                
                if success:
                    # Add as a skill too
                    self.self_prog.skills.add_skill(
                        name.replace('.py', ''),
                        action_dict.get('reasoning', 'New module'),
                        code
                    )
                
                return msg
            
            elif action == 'remember':
                if not self.self_prog:
                    return "Memory not available"
                
                key = action_dict.get('key', '')
                value = action_dict.get('value', '')
                
                self.self_prog.memory.data["user_preferences"][key] = value
                self.self_prog.memory.save()
                return f"Remembered: {key}"
            
            elif action == 'train_self':
                # UNLIMITED SELF-TRAINING - Nova learns new skills
                if not self.self_prog:
                    return "Self-programming not available"
                
                skill = action_dict.get('skill', '')
                pattern = action_dict.get('pattern', '')
                examples = action_dict.get('examples', [])
                
                # Store in training data
                training_entry = {
                    "skill": skill,
                    "pattern": pattern,
                    "examples": examples,
                    "timestamp": datetime.now().isoformat()
                }
                self.self_prog.memory.data["training_data"].append(training_entry)
                
                # Also add to patterns for future reference
                if "learned_skills" not in self.self_prog.memory.data["patterns"]:
                    self.self_prog.memory.data["patterns"]["learned_skills"] = []
                self.self_prog.memory.data["patterns"]["learned_skills"].append(training_entry)
                
                # Save to skills library for reuse
                if pattern:
                    self.self_prog.skills.add_skill(
                        skill.replace(' ', '_').lower(),
                        skill,
                        pattern
                    )
                
                self.self_prog.memory.save()
                
                return f"✅ TRAINED: {skill}. Pattern stored. {len(examples)} examples recorded. Skill added to library."
                
            elif action == 'chat':
                message = action_dict.get('message', '')
                print(f"  💬 Nova: {message}")
                return f"Said: {message}"

            elif action == 'finish':
                return action_dict.get('result', 'Task completed')

            else:
                return f"Unknown action: {action}"
                
        except Exception as e:
            return f"Execution Error: {str(e)}"
    
    def train_from_feedback(self, feedback: str, was_successful: bool):
        """
        Learn from user feedback after a task.
        """
        if self.self_prog:
            last_goal = self.history[0]['content'] if self.history else "Unknown"
            self.self_prog.train_on_task(last_goal, feedback, was_successful)
            print(f"📚 Training recorded: {'✅' if was_successful else '❌'}")
