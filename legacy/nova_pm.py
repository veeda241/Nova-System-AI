#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Project Management Automation
==================================
Automated project tracking, reporting, and documentation.
- Auto README updates
- Issue tracking (Local)
- Progress logs
- Weekly reports
"""

import os
import sys
import json
import time
from datetime import datetime
import glob

# Try to import Nova AI logic
try:
    from groq import Groq
    import dotenv
    dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "Config", ".env"))
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_AVAILABLE = True if GROQ_API_KEY else False
except ImportError:
    GROQ_AVAILABLE = False

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

class ProjectManager:
    """Manages project documentation, issues, and progress."""
    
    def __init__(self, project_root="."):
        self.project_root = os.path.abspath(project_root)
        self.issues_file = os.path.join(self.project_root, ".nova_issues.json")
        self.work_log_file = os.path.join(self.project_root, ".nova_worklog.json")
        self.client = Groq(api_key=GROQ_API_KEY) if GROQ_AVAILABLE and GROQ_API_KEY else None
        self.model = "llama-3.3-70b-versatile"

    def _call_ai(self, prompt: str) -> str:
        if not self.client:
            return "AI not available."
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"

    # --- README AUTOMATION ---
    def generate_readme(self) -> str:
        """Scan project files and generate a comprehensive README.md."""
        files = []
        for ext in ['*.py', '*.js', '*.html', '*.css', '*.md']:
            files.extend(glob.glob(os.path.join(self.project_root, "**", ext), recursive=True))
        
        # Limit to top 10 files to avoid context overflow, prioritizing root
        files = sorted(files, key=lambda x: x.count(os.sep))[:10]
        
        code_context = ""
        for f in files:
            if "node_modules" in f or ".venv" in f or ".git" in f:
                continue
            try:
                rel_path = os.path.relpath(f, self.project_root)
                with open(f, 'r', encoding='utf-8', errors='ignore') as file:
                    content = file.read(2000) # Read first 2k chars
                    code_context += f"\n--- File: {rel_path} ---\n{content}\n"
            except:
                pass

        prompt = f"""
        Generate a professional README.md for this software project based on the following code samples.
        Include:
        - Project Title & Description
        - Key Features
        - Tech Stack
        - Installation/Setup
        - Usage Guide
        
        Code Context:
        {code_context}
        """
        return self._call_ai(prompt)

    def update_readme(self):
        """Generate and save README.md."""
        readme_content = self.generate_readme()
        target = os.path.join(self.project_root, "README_NEW.md")
        with open(target, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        return target

    # --- ISSUE TRACKING ---
    def load_issues(self):
        if os.path.exists(self.issues_file):
            with open(self.issues_file, 'r') as f:
                return json.load(f)
        return []

    def save_issues(self, issues):
        with open(self.issues_file, 'w') as f:
            json.dump(issues, f, indent=2)

    def add_issue(self, title, description, priority="Medium"):
        issues = self.load_issues()
        issue = {
            "id": len(issues) + 1,
            "title": title,
            "description": description,
            "status": "Open",
            "priority": priority,
            "created_at": datetime.now().isoformat()
        }
        issues.append(issue)
        self.save_issues(issues)
        return issue

    def list_issues(self):
        return self.load_issues()

    def close_issue(self, issue_id):
        issues = self.load_issues()
        for i in issues:
            if i['id'] == int(issue_id):
                i['status'] = 'Closed'
                i['closed_at'] = datetime.now().isoformat()
                self.save_issues(issues)
                return True
        return False

    # --- PROGRESS LOGGING ---
    def log_work(self, message):
        logs = []
        if os.path.exists(self.work_log_file):
            with open(self.work_log_file, 'r') as f:
                logs = json.load(f)
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "message": message
        }
        logs.append(log_entry)
        
        with open(self.work_log_file, 'w') as f:
            json.dump(logs, f, indent=2)
        return True

    def generate_weekly_report(self):
        """Analyze work logs and generate a weekly report."""
        if not os.path.exists(self.work_log_file):
            return "No work logs found."
            
        with open(self.work_log_file, 'r') as f:
            logs = json.load(f)
        
        # Filter (conceptually, for now use all)
        log_text = "\n".join([f"- {l['timestamp'][:10]}: {l['message']}" for l in logs[-20:]]) # Last 20 entries
        
        prompt = f"""
        Generate a Weekly Progress Report based on these work logs.
        Focus on identifying key achievements, blockers resolved, and overall momentum.
        Style: Professional Engineering Manager format.
        
        Work Logs:
        {log_text}
        """
        return self._call_ai(prompt)

# Global Instance
PM = ProjectManager()

def start_pm_mode():
    """Interactive CLI for Project Management Mode."""
    if RICH_AVAILABLE:
        console.clear()
        console.print(Panel.fit(
            "[bold green]🚀 NOVA PROJECT MANAGER[/]\n"
            "[dim]DevOps & Engineering Ops Automation[/]",
            border_style="green"
        ))
    else:
        print("\n=== NOVA PROJECT MANAGER ===\n")

    while True:
        if RICH_AVAILABLE:
            console.print("\n[bold yellow]Select Action:[/]")
            console.print("1. [white]📄 Auto-Generate README[/]")
            console.print("2. [white]🐞 Issue Tracker[/]")
            console.print("3. [white]📝 Log Progress[/]")
            console.print("4. [white]📊 Generate Weekly Report[/]")
            console.print("5. [white]🔙 Exit[/]")
            choice = input("\nChoose (1-5): ").strip()
        else:
            print("\nACTIONS:")
            print("1. Auto-Generate README")
            print("2. Issue Tracker")
            print("3. Log Progress")
            print("4. Generate Weekly Report")
            print("5. Exit")
            choice = input("\nChoose (1-5): ").strip()

        if choice == '1':
            print("\nScanning project files...")
            try:
                path = PM.update_readme()
                print(f"✅ README generated at: {path}")
                print("Review it before replacing your main README.md")
            except Exception as e:
                print(f"Error: {e}")

        elif choice == '2':
            print("\n--- ISSUE TRACKER ---")
            print("1. List Issues")
            print("2. Add Issue")
            print("3. Close Issue")
            sub = input("Select: ").strip()
            
            if sub == '1':
                issues = PM.list_issues()
                if RICH_AVAILABLE:
                    table = Table(title="Project Issues")
                    table.add_column("ID", style="cyan")
                    table.add_column("Status", style="magenta")
                    table.add_column("Priority", style="yellow")
                    table.add_column("Title")
                    for i in issues:
                        table.add_row(str(i['id']), i['status'], i['priority'], i['title'])
                    console.print(table)
                else:
                    for i in issues:
                        print(f"[{i['id']}] {i['status']} - {i['title']}")
            
            elif sub == '2':
                title = input("Title: ")
                desc = input("Description: ")
                prio = input("Priority (Low/Medium/High): ")
                PM.add_issue(title, desc, prio)
                print("✅ Issue added.")
                
            elif sub == '3':
                iid = input("Issue ID to close: ")
                if PM.close_issue(iid):
                    print("✅ Issue closed.")
                else:
                    print("❌ Issue not found.")

        elif choice == '3':
            msg = input("\nWhat did you work on? ")
            if msg:
                PM.log_work(msg)
                print("✅ Work logged.")

        elif choice == '4':
            print("\nGenerating Report...")
            report = PM.generate_weekly_report()
            if RICH_AVAILABLE:
                console.print(Panel(Markdown(report), title="Weekly Report", border_style="blue"))
            else:
                print(report)

        elif choice == '5':
            break

if __name__ == "__main__":
    start_pm_mode()
