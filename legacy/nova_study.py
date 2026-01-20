#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Study & Research Engine
============================
AI-powered study automation and research assistance.
- Summarizes PDFs
- Organizes notes
- Extracts key points
- Creates revision sheets
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
import textwrap

# Try to import necessary libraries
try:
    from pypdf import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from groq import Groq
    import dotenv
    dotenv.load_dotenv(os.path.join(os.path.dirname(__file__), "Config", ".env"))
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_AVAILABLE = True if GROQ_API_KEY else False
except ImportError:
    GROQ_AVAILABLE = False
    GROQ_API_KEY = None

# Rich UI Support
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    console = None

class StudyEngine:
    """
    AI Study Assistant for summarizing content and creating study materials.
    """
    
    def __init__(self):
        self.model = "llama-3.3-70b-versatile"
        self.client = None
        if GROQ_AVAILABLE and GROQ_API_KEY:
            self.client = Groq(api_key=GROQ_API_KEY)
    
    def _call_ai(self, prompt: str, system_prompt: str = "You are an expert academic tutor and research assistant.") -> str:
        """Helper to call Groq API."""
        if not self.client:
            return "Error: AI engine not available. Please check Groq API key."
            
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2048
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"AI Error: {str(e)}"

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file."""
        if not PDF_AVAILABLE:
            return "Error: pypdf library not installed. Run: pip install pypdf"
        
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            return f"Error reading PDF: {str(e)}"

    def summarize_content(self, text: str, focus: str = "general") -> str:
        """Summarize text content with specific focus."""
        if not text.strip():
            return "Error: No text provided."
            
        # Truncate text if too long (approx 15k chars is a safe instruction limit for 70b)
        if len(text) > 15000:
            text = text[:15000] + "...(truncated)"
            
        prompt = f"""
        Please provide a comprehensive summary of the following text.
        Focus: {focus}
        
        Text to summarize:
        {text}
        
        Output Format:
        # Title
        ## Executive Summary
        ## Key Concepts
        ## Detailed Breakdown
        """
        return self._call_ai(prompt, "You are an expert researcher. Summarize complex information clearly.")

    def organize_notes(self, text: str) -> str:
        """Organize unstructured notes into a structured format."""
        prompt = f"""
        Organize the following unstructured notes into a clean, hierarchical structure.
        Use Markdown formatting with headers, bullet points, and bold text for emphasis.
        
        Notes:
        {text}
        """
        return self._call_ai(prompt, "You are a meticulous note-taker. Organize information logically.")

    def extract_key_points(self, text: str) -> str:
        """Extract crucial key points and definitions."""
        prompt = f"""
        Extract the most important key points, definitions, and facts from this text.
        Format as a list of bullet points.
        
        Text:
        {text}
        """
        return self._call_ai(prompt)

    def create_revision_sheet(self, text: str) -> str:
        """Generate a revision sheet with Q&A and summary tables."""
        prompt = f"""
        Create a study revision sheet from this content.
        Include:
        1. Quick Recap (3 sentences)
        2. Top 5 Definitions
        3. 10 Review Questions (with answers hidden or separate, but for now just list Q&A pairs)
        4. A 'Cheat Sheet' table of key data/formulas/concepts.
        
        Text:
        {text}
        """
        return self._call_ai(prompt, "You are a teacher creating study materials for students.")


# Global Instance
STUDY_ENGINE = StudyEngine()


def start_study_mode():
    """Interactive CLI for Study Mode."""
    if RICH_AVAILABLE:
        console.clear()
        console.print(Panel.fit(
            "[bold cyan]📚 NOVA STUDY & RESEARCH ENGINE[/]\n"
            "[dim]Powering your learning with AI[/]",
            border_style="cyan"
        ))
    else:
        print("\n=== NOVA STUDY & RESEARCH ENGINE ===\n")

    if not PDF_AVAILABLE:
        print("⚠️  Warning: 'pypdf' not found. PDF features will be disabled.")
        print("   Install: pip install pypdf\n")

    if not GROQ_AVAILABLE:
        print("⚠️  Warning: Groq API key not found. AI features will be disabled.\n")

    while True:
        if RICH_AVAILABLE:
            console.print("\n[bold yellow]Select Action:[/]")
            console.print("1. [white]📄 Summarize PDF[/]")
            console.print("2. [white]📝 Organize Notes[/]")
            console.print("3. [white]🔑 Extract Key Points[/]")
            console.print("4. [white]📖 Create Revision Sheet[/]")
            console.print("5. [white]🔙 Exit[/]")
            choice = input("\nChoose (1-5): ").strip()
        else:
            print("\nACTIONS:")
            print("1. Summarize PDF")
            print("2. Organize Notes")
            print("3. Extract Key Points")
            print("4. Create Revision Sheet")
            print("5. Exit")
            choice = input("\nChoose (1-5): ").strip()

        if choice == '1':
            file_path = input("\nEnter PDF path: ").strip().strip('"')
            if os.path.exists(file_path):
                if RICH_AVAILABLE:
                    with console.status("[bold green]Reading PDF..."):
                        text = STUDY_ENGINE.extract_text_from_pdf(file_path)
                    if text.startswith("Error"):
                        console.print(f"[red]{text}[/]")
                        continue
                        
                    with console.status("[bold cyan]Generating Summary..."):
                        summary = STUDY_ENGINE.summarize_content(text)
                    
                    console.print(Panel(Markdown(summary), title="Summary", border_style="green"))
                else:
                    print("Reading PDF...")
                    text = STUDY_ENGINE.extract_text_from_pdf(file_path)
                    print("Generating Summary...")
                    print(STUDY_ENGINE.summarize_content(text))
            else:
                print("❌ File not found.")

        elif choice == '2':
            print("\nEnter your notes (type END on a new line to finish):")
            lines = []
            while True:
                line = input()
                if line.strip().upper() == 'END':
                    break
                lines.append(line)
            notes = "\n".join(lines)
            
            if notes:
                if RICH_AVAILABLE:
                    with console.status("[bold cyan]Organizing..."):
                        organized = STUDY_ENGINE.organize_notes(notes)
                    console.print(Panel(Markdown(organized), title="Organized Notes", border_style="blue"))
                else:
                    print(STUDY_ENGINE.organize_notes(notes))

        elif choice == '3':
            # Could accept file or text input
            print("\nInput source:")
            print("1. Text Input")
            print("2. PDF File")
            src = input("Choice: ").strip()
            
            text = ""
            if src == '2':
                file_path = input("Enter PDF path: ").strip().strip('"')
                if os.path.exists(file_path):
                     text = STUDY_ENGINE.extract_text_from_pdf(file_path)
                else:
                    print("File not found.")
                    continue
            else:
                input("Press Enter to paste text, then Ctrl+Z/D to submit (or just type short text):")
                # Simple single line for now to avoid complexity in CLI
                text = input("Text: ")

            if text:
                if RICH_AVAILABLE:
                    with console.status("[bold cyan]Extracting Key Points..."):
                        points = STUDY_ENGINE.extract_key_points(text)
                    console.print(Panel(Markdown(points), title="Key Points", border_style="yellow"))
                else:
                    print(STUDY_ENGINE.extract_key_points(text))

        elif choice == '4':
            # Revision sheet from file
            file_path = input("\nEnter PDF/Text file path for revision content: ").strip().strip('"')
            if os.path.exists(file_path):
                if file_path.endswith('.pdf'):
                    text = STUDY_ENGINE.extract_text_from_pdf(file_path)
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        text = f.read()
                
                if RICH_AVAILABLE:
                    with console.status("[bold cyan]Creating Revision Sheet..."):
                        sheet = STUDY_ENGINE.create_revision_sheet(text)
                    console.print(Panel(Markdown(sheet), title="Revision Sheet", border_style="magenta"))
                else:
                    print(STUDY_ENGINE.create_revision_sheet(text))
            else:
                print("File not found.")

        elif choice == '5':
            break

if __name__ == "__main__":
    start_study_mode()
