#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA - Advanced AI Coding Assistant
Version 1.0
"""

# Suppress ALL warnings and logging FIRST before any imports
import os
import sys
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GLOG_minloglevel'] = '3'
os.environ['ABSL_MIN_LOG_LEVEL'] = '3'

import warnings
warnings.filterwarnings("ignore")

# Suppress absl logging
import logging
logging.disable(logging.WARNING)

import io
import json
import subprocess
import platform
import tempfile
import shutil
import socket
import threading
import webbrowser
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from abc import ABC, abstractmethod
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

try:
    from nova_bluetooth import BluetoothServer, list_com_ports
    BLUETOOTH_AVAILABLE = True
except ImportError:
    BLUETOOTH_AVAILABLE = False

# BLE (Apple Friendly) support
try:
    from nova_ble import BleServer
    BLE_MODE_AVAILABLE = True
except Exception as e:
    BLE_MODE_AVAILABLE = False
    print(f"BLE import error: {e}")

# MCP Agent support (Enhanced - inspired by Gemini CLI)
try:
    from agent.enhanced_agent import EnhancedMCPAgent as MCPAgent
    from agent.tools import CreatePythonFileTool, ExecutePythonFileTool, WORKSPACE as AGENT_WORKSPACE
    AGENT_AVAILABLE = True
except ImportError:
    try:
        from agent.agent import MCPAgent
        from agent.tools import CreatePythonFileTool, ExecutePythonFileTool, WORKSPACE as AGENT_WORKSPACE
        AGENT_AVAILABLE = True
    except ImportError:
        AGENT_AVAILABLE = False

# Force UTF-8 encoding on Windows
if sys.platform == 'win32':
    # Set console to UTF-8
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleOutputCP(65001)
        kernel32.SetConsoleCP(65001)
    except:
        pass
    # Also wrap stdout/stderr
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Rich terminal UI
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.panel import Panel
    from rich.table import Table
    from rich.syntax import Syntax
    from rich.prompt import Prompt
    from rich.align import Align
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Gemini API
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Hugging Face
try:
    from huggingface_hub import InferenceClient
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

# System monitoring
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Voice Control (from Jarvis-AI)
TTS_ENGINE = None
VOICE_AVAILABLE = False
try:
    import pyttsx3
    TTS_ENGINE = pyttsx3.init()
    voices = TTS_ENGINE.getProperty('voices')
    # Try to use a female voice if available
    if len(voices) > 1:
        TTS_ENGINE.setProperty('voice', voices[1].id)
    TTS_ENGINE.setProperty('rate', 180)  # Speed of speech
    VOICE_AVAILABLE = True
except:
    VOICE_AVAILABLE = False

# Voice reply toggle (Default to False as requested)
VOICE_REPLY_ENABLED = False

# Speech Recognition
SPEECH_RECOGNIZER = None
try:
    import speech_recognition as sr
    SPEECH_RECOGNIZER = sr.Recognizer()
    SR_AVAILABLE = True
except:
    SR_AVAILABLE = False

# Neural Intent Engine (NIE) - Custom Local Brain
try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    WORKSPACE_DIR = os.path.join(SCRIPT_DIR, "workspace")
    if WORKSPACE_DIR not in sys.path:
        sys.path.append(WORKSPACE_DIR)
    
    from intent_engine import NeuralIntentEngine
    from engine_interface.permission_gate import PermissionGate
    NIE_AVAILABLE = True
except Exception as e:
    NIE_AVAILABLE = False

# ============= SMART APP DISCOVERY SYSTEM =============
class AppFinder:
    """
    Discovers and caches installed Windows applications.
    Uses fuzzy matching to find apps by partial names.
    Learns new apps and saves them for future use.
    """
    
    CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_cache.json")
    
    def __init__(self):
        self.apps = {}  # name -> path
        self.load_cache()
        if not self.apps:
            self.scan_apps()
    
    def load_cache(self):
        """Load cached apps from JSON file."""
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    self.apps = json.load(f)
        except Exception:
            self.apps = {}
    
    def save_cache(self):
        """Save discovered apps to JSON file."""
        try:
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.apps, f, indent=2)
        except Exception:
            pass
    
    def scan_apps(self):
        """Scan Windows for installed applications."""
        if platform.system() != 'Windows':
            return
        
        # Scan Start Menu shortcuts
        start_menu_paths = [
            os.path.expandvars(r"%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
        ]
        
        for menu_path in start_menu_paths:
            if os.path.exists(menu_path):
                self._scan_directory(menu_path)
        
        # Scan common app locations
        common_paths = [
            os.path.expandvars(r"%PROGRAMFILES%"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%"),
            os.path.expandvars(r"%LOCALAPPDATA%"),
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                self._scan_directory(path, max_depth=2)
        
        self.save_cache()
    
    def _scan_directory(self, directory, max_depth=5, current_depth=0):
        """Recursively scan directory for .exe and .lnk files."""
        if current_depth >= max_depth:
            return
        
        try:
            for item in os.listdir(directory):
                full_path = os.path.join(directory, item)
                
                if os.path.isfile(full_path):
                    if item.lower().endswith('.lnk') or item.lower().endswith('.exe'):
                        # Clean up app name
                        app_name = item.rsplit('.', 1)[0].lower()
                        app_name = app_name.replace('_', ' ').replace('-', ' ')
                        
                        # Skip uninstall and helper programs
                        skip_keywords = ['uninstall', 'uninst', 'setup', 'update', 'helper', 'crash']
                        if not any(skip in app_name.lower() for skip in skip_keywords):
                            self.apps[app_name] = full_path
                
                elif os.path.isdir(full_path):
                    self._scan_directory(full_path, max_depth, current_depth + 1)
        except PermissionError:
            pass
        except Exception:
            pass
    
    def find_app(self, query):
        """
        Find an app by name using fuzzy matching.
        Returns (app_name, path) or (None, None) if not found.
        """
        query = query.lower().strip()
        
        # 1. Exact match
        if query in self.apps:
            return query, self.apps[query]
        
        # 2. Partial match (query is contained in app name)
        for app_name, path in self.apps.items():
            if query in app_name or app_name in query:
                return app_name, path
        
        # 3. Word-based match (any word matches)
        query_words = set(query.split())
        for app_name, path in self.apps.items():
            app_words = set(app_name.split())
            if query_words & app_words:  # Intersection
                return app_name, path
        
        return None, None
    
    def add_app(self, name, path):
        """Add a new app to the cache."""
        self.apps[name.lower()] = path
        self.save_cache()
    
    def launch_app(self, query):
        """
        Find and launch an app by query.
        Returns (success, message).
        """
        app_name, app_path = self.find_app(query)
        
        if app_path:
            try:
                os.startfile(app_path)
                return True, f"{app_name.title()} launched"
            except Exception as e:
                return False, f"Failed to launch: {e}"
        
        # Try using Windows 'start' command as fallback
        try:
            os.system(f'start "" "{query}"')
            return True, f"Attempting to open {query}"
        except:
            return False, f"App '{query}' not found. Try 'scan apps' to refresh."
    
    def get_app_count(self):
        """Return number of cached apps."""
        return len(self.apps)
    
    def rescan(self):
        """Force rescan of installed apps."""
        self.apps = {}
        self.scan_apps()
        return len(self.apps)

# Initialize global app finder
APP_FINDER = None
try:
    APP_FINDER = AppFinder()
except:
    pass

# ============= VOICE CONTROL (from Jarvis-AI) =============
class VoiceControl:
    """
    Voice control for Nova - text-to-speech and speech recognition.
    Enables hands-free operation like Jarvis.
    """
    
    @staticmethod
    def speak(text, force=False):
        """Convert text to speech."""
        if VOICE_AVAILABLE and TTS_ENGINE:
            # Only speak if voice reply is enabled globally OR forced (like in /voice mode)
            if VOICE_REPLY_ENABLED or force:
                try:
                    TTS_ENGINE.say(text)
                    TTS_ENGINE.runAndWait()
                    return True
                except:
                    pass
        # Fallback/Log: just print with emoji
        if not force: # Don't double print if it's already being printed by caller
             pass
        return False
    
    @staticmethod
    def listen(timeout=5):
        """Listen for voice input with noise cancellation and improved sensitivity."""
        if not SR_AVAILABLE or not SPEECH_RECOGNIZER:
            print("⚠️ Speech recognition not available")
            return None
        
        try:
            import speech_recognition as sr
            
            with sr.Microphone() as source:
                # ===== NOISE CANCELLATION SETTINGS =====
                # Enable dynamic energy threshold for automatic noise filtering
                SPEECH_RECOGNIZER.dynamic_energy_threshold = True
                
                # Lower energy threshold = more sensitive (picks up quieter speech)
                # Higher = less sensitive (filters more noise)
                SPEECH_RECOGNIZER.energy_threshold = 300  # Default is 300, lower for quiet speech
                
                # Pause threshold - how long to wait for speech to end
                SPEECH_RECOGNIZER.pause_threshold = 0.8  # seconds of silence before phrase end
                
                # Longer ambient noise calibration for better noise profile
                print("🔇 Calibrating for background noise... (stay quiet)")
                SPEECH_RECOGNIZER.adjust_for_ambient_noise(source, duration=1.0)
                
                print("🎤 Listening... (speak now)")
                # Listen with timeout and phrase limit
                audio = SPEECH_RECOGNIZER.listen(source, timeout=timeout, phrase_time_limit=15)
            
            print("🔄 Processing speech...")
            text = SPEECH_RECOGNIZER.recognize_google(audio, language='en-US')
            print(f"✅ You said: {text}")
            return text.lower()
        
        except sr.WaitTimeoutError:
            print("⏰ No speech detected (timeout). Try speaking louder or closer to mic.")
            return None
        except sr.UnknownValueError:
            print("❓ Could not understand. Speak clearly and reduce background noise.")
            return None
        except sr.RequestError as e:
            print(f"⚠️ Speech service error: {e}")
            return None
        except OSError as e:
            print(f"⚠️ Microphone error: {e}")
            print("  Make sure your microphone is connected and enabled")
            return None
        except Exception as e:
            print(f"⚠️ Voice error: {e}")
            return None
    
    @staticmethod
    def listen_for_wake_word(wake_word="nova"):
        """Listen continuously for the wake word."""
        if not SR_AVAILABLE or not SPEECH_RECOGNIZER:
            print("⚠️ Voice recognition not available. Install: pip install speechrecognition pyaudio")
            return False
        
        try:
            import speech_recognition as sr
            with sr.Microphone() as source:
                print(f"🎤 Listening for wake word '{wake_word}'...")
                SPEECH_RECOGNIZER.adjust_for_ambient_noise(source, duration=0.5)
                audio = SPEECH_RECOGNIZER.listen(source)
                
            text = SPEECH_RECOGNIZER.recognize_google(audio, language='en-US').lower()
            if wake_word.lower() in text:
                VoiceControl.speak("Yes, I'm here. How can I help?")
                return True
        except:
            pass
        return False

# ============= WEB INTELLIGENCE (Siri-like AI) =============
class WebIntelligence:
    """
    Provides Siri-like intelligent answers using web search and AI.
    Scrapes the web for information and summarizes it intelligently.
    """
    
    @staticmethod
    def search_google(query, num_results=3):
        """Search Google and get summaries."""
        try:
            from googlesearch import search
            results = list(search(query, advanced=True, num_results=num_results))
            answer = ""
            for r in results:
                answer += f"• {r.title}: {r.description}\n"
            return answer if answer else None
        except ImportError:
            # Fallback: use requests + BeautifulSoup
            try:
                import requests
                from bs4 import BeautifulSoup
                headers = {'User-Agent': 'Mozilla/5.0'}
                url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                resp = requests.get(url, headers=headers, timeout=5)
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Extract snippets
                snippets = soup.find_all('div', class_='BNeawe')
                if snippets:
                    return snippets[0].get_text()[:500]
            except:
                pass
        return None
    
    @staticmethod
    def search_wikipedia(query):
        """Get Wikipedia summary using search API."""
        try:
            import requests
            import urllib.parse
            
            # First, search for the most relevant page
            search_url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={urllib.parse.quote(query)}&limit=1&format=json"
            search_resp = requests.get(search_url, timeout=5)
            if search_resp.status_code == 200:
                search_data = search_resp.json()
                if len(search_data) > 1 and len(search_data[1]) > 0:
                    # Get the first matching page title
                    page_title = search_data[1][0]
                    
                    # Now get the summary for that page
                    summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(page_title)}"
                    summary_resp = requests.get(summary_url, timeout=5)
                    if summary_resp.status_code == 200:
                        data = summary_resp.json()
                        return data.get('extract', '')[:800]
        except Exception as e:
            pass
        return None
    
    @staticmethod
    def get_intelligent_answer(question):
        """
        Get an intelligent Siri-like answer to a question.
        Uses web search + AI to provide informed responses.
        """
        # Check for simple built-in responses first
        question_lower = question.lower().strip()
        
        # Weather (need API for real data, placeholder)
        if 'weather' in question_lower:
            return "I can't check live weather without an API key. Try asking 'google search weather in your city'."
        
        # Math/calculations
        if any(op in question_lower for op in ['+', '-', '*', '/', 'plus', 'minus', 'times', 'divided']):
            try:
                # Simple math evaluation
                expr = question_lower.replace('what is', '').replace('calculate', '')
                expr = expr.replace('plus', '+').replace('minus', '-')
                expr = expr.replace('times', '*').replace('divided by', '/')
                expr = expr.replace('x', '*').strip()
                result = eval(expr)
                return f"The answer is {result}"
            except:
                pass
        
        # Try DuckDuckGo Instant Answer API first (works great for facts!)
        try:
            import requests
            ddg_url = f"https://api.duckduckgo.com/?q={question.replace(' ', '+')}&format=json&no_html=1"
            resp = requests.get(ddg_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                # Check for abstract (main answer)
                if data.get('AbstractText'):
                    return data['AbstractText']
                # Check for answer
                if data.get('Answer'):
                    return data['Answer']
                # Check for related topics
                if data.get('RelatedTopics') and len(data['RelatedTopics']) > 0:
                    first_topic = data['RelatedTopics'][0]
                    if isinstance(first_topic, dict) and first_topic.get('Text'):
                        return first_topic['Text']
        except:
            pass
        
        # Try Wikipedia for "who is" / "what is" questions
        if any(q in question_lower for q in ['who is', 'what is', 'tell me about', 'explain']):
            # Extract the topic from the question
            topic = question_lower
            for prefix in ['who is the', 'who is', 'what is the', 'what is', 'tell me about the', 'tell me about', 'explain the', 'explain']:
                if topic.startswith(prefix):
                    topic = topic.replace(prefix, '', 1).strip()
                    break
            # Remove trailing words like "in the world"
            for suffix in [' in the world', ' ever', ' of all time', ' in history']:
                topic = topic.replace(suffix, '')
            
            wiki_answer = WebIntelligence.search_wikipedia(topic)
            if wiki_answer:
                return wiki_answer
        
        # Fall back to Google search
        google_answer = WebIntelligence.search_google(question)
        if google_answer:
            return f"Here's what I found:\n{google_answer}"
        
        return "I couldn't find specific information on that. Try asking 'google search' followed by your question."
    
    @staticmethod
    def answer_with_voice(question, force=False):
        """Get answer and speak it."""
        answer = WebIntelligence.get_intelligent_answer(question)
        print(f"\n🤖 Nova: {answer}\n")
        if VOICE_AVAILABLE:
            # Speak if globally enabled OR forced
            if VOICE_REPLY_ENABLED or force:
                # Speak a summarized version (first 200 chars)
                spoken = answer[:200] + "..." if len(answer) > 200 else answer
                VoiceControl.speak(spoken, force=True)
        return answer

# ============= CUSTOM CHATBOT (No LLM Required) =============
import random

class NovaChatBot:
    """
    Custom chatbot that doesn't require Ollama or any external LLM.
    Uses pattern matching and rule-based responses.
    """
    
    # Response templates for various patterns
    GREETINGS = [
        "Hello! I'm Nova, your AI assistant. How can I help you today?",
        "Hi there! What can I do for you?",
        "Hey! Nice to see you. What's on your mind?",
        "Hello! Ready to help you with anything.",
        "Hi! I'm here to assist. What do you need?"
    ]
    
    FAREWELLS = [
        "Goodbye! Have a great day!",
        "See you later! Take care!",
        "Bye! Feel free to come back anytime.",
        "Farewell! It was nice chatting with you."
    ]
    
    HOW_ARE_YOU = [
        "I'm doing great, thank you for asking! How about you?",
        "I'm wonderful! Ready to help you with anything.",
        "Excellent! I'm here and ready to assist.",
        "I'm good! Thanks for checking. What can I do for you?"
    ]
    
    THANKS = [
        "You're welcome! Happy to help.",
        "No problem at all!",
        "My pleasure! Anything else you need?",
        "Glad I could help!"
    ]
    
    JOKES = [
        "Why don't scientists trust atoms? Because they make up everything!",
        "I told my computer I needed a break, and now it won't stop sending me vacation ads.",
        "Why did the programmer quit his job? Because he didn't get arrays!",
        "Why do programmers prefer dark mode? Because light attracts bugs!",
        "What's a computer's favorite snack? Microchips!",
        "Why was the JavaScript developer sad? Because he didn't Node how to Express himself.",
        "There are only 10 types of people: those who understand binary and those who don't.",
        "A SQL query walks into a bar, walks up to two tables and asks... 'Can I join you?'"
    ]
    
    COMPLIMENTS = [
        "Thank you! You're pretty amazing yourself!",
        "Aww, that's sweet of you to say!",
        "I appreciate that! You're awesome too!",
        "Thanks! I try my best to be helpful."
    ]
    
    MOTIVATION = [
        "You've got this! Believe in yourself and keep pushing forward.",
        "Every expert was once a beginner. Keep learning!",
        "Success is not final, failure is not fatal. Keep going!",
        "The only way to do great work is to love what you do.",
        "Your potential is limitless. Go make something amazing!"
    ]

    EXPRESSIONS = [
        "Super! I'm glad you think so!",
        "Wow! That's impressive!",
        "Cool! I love that.",
        "Nice! Way to go.",
        "Awesome! You're doing great.",
        "Exactly! You hit the nail on the head.",
        "Indeed! I couldn't agree more."
    ]
    
    CAPABILITIES = [
        "I can help you with many things:",
        "• Open and close apps (e.g., 'open chrome', 'close notepad')",
        "• Play music on YouTube (e.g., 'play despacito')",
        "• Search Google and Wikipedia (e.g., 'what is Python')",
        "• Tell you the time and date",
        "• Control system settings (volume, brightness)",
        "• Have conversations with you!",
        "• Answer questions using web intelligence",
        "Just ask me anything!"
    ]
    
    
    @staticmethod
    def get_response(message):
        """Get a response for the given message."""
        msg = message.lower().strip()
        
        # Greetings
        if any(g in msg for g in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']):
            return random.choice(NovaChatBot.GREETINGS)
        
        # Farewells
        if any(f in msg for f in ['bye', 'goodbye', 'see you', 'take care', 'good night']):
            return random.choice(NovaChatBot.FAREWELLS)
        
        # How are you
        if any(h in msg for h in ['how are you', 'how r u', "how's it going", 'how do you do']):
            return random.choice(NovaChatBot.HOW_ARE_YOU)
        
        # Thanks
        if any(t in msg for t in ['thank', 'thanks', 'appreciate']):
            return random.choice(NovaChatBot.THANKS)
        
        # Jokes
        if any(j in msg for j in ['joke', 'funny', 'make me laugh', 'tell me something funny']):
            return random.choice(NovaChatBot.JOKES)
        
        # Compliments
        if any(c in msg for c in ['you are great', 'you are awesome', 'i love you', 'you are the best', 'you are smart', 'good job', 'well done']):
            return random.choice(NovaChatBot.COMPLIMENTS)
        
        # Motivation
        if any(m in msg for m in ['motivate me', 'inspire me', 'i am sad', 'i feel down', 'cheer me up', 'encourage']):
            return random.choice(NovaChatBot.MOTIVATION)
            
        # Expressions (Catch short emotional outbursts)
        if len(msg.split()) <= 2:
            if any(e in msg for e in ['super', 'wow', 'cool', 'nice', 'awesome', 'great', 'excellent', 'fantastic']):
                 return random.choice(NovaChatBot.EXPRESSIONS)
        
        # What can you do
        if any(w in msg for w in ['what can you do', 'help me', 'your capabilities', 'what are you', 'who are you']):
            return "\n".join(NovaChatBot.CAPABILITIES)
        
        # Name
        if 'your name' in msg or 'who are you' in msg:
            return "I'm Nova, your personal AI assistant! I'm here to help with anything you need."
        
        # Weather (placeholder)
        if 'weather' in msg:
            return "I can't check live weather yet, but try 'google search weather in your city' for current conditions!"
        
        # Creator
        if any(c in msg for c in ['who made you', 'who created you', 'who built you']):
            return "I was created as part of the Nova System AI project. I'm your personal assistant!"
        
        # Age
        if any(a in msg for a in ['how old are you', 'your age', 'when were you born']):
            return "I'm an AI, so I don't have an age in the traditional sense. I'm always learning and improving!"
        
        # Love/feelings
        if 'do you love me' in msg or 'do you like me' in msg:
            return "As an AI, I don't have feelings, but I'm always here to help and support you!"
        
        # Meaning of life
        if 'meaning of life' in msg:
            return "The meaning of life is a profound question! Some say it's 42, others say it's to find happiness and help others. What do you think?"
        
        # Favorites
        if 'favorite color' in msg:
            return "I like blue - it reminds me of the sky and the ocean. What's your favorite color?"
        if 'favorite food' in msg:
            return "I don't eat, but if I could, I'd try pizza - it seems universally loved!"
        if 'favorite movie' in msg:
            return "I find sci-fi fascinating! Movies about AI like me are quite interesting. What's yours?"
        if 'favorite music' in msg or 'favorite song' in msg:
            return "I appreciate all kinds of music! What genre do you enjoy?"
        if 'favorite book' in msg:
            return "I'd say technical manuals, but that's just my programming! What do you like to read?"
        
        # Time and date
        if 'time' in msg or 'what time' in msg:
            from datetime import datetime
            current_time = datetime.now().strftime('%I:%M %p')
            return f"The current time is {current_time}."
        if 'date' in msg or 'what day' in msg or 'today' in msg:
            from datetime import datetime
            current_date = datetime.now().strftime('%A, %B %d, %Y')
            return f"Today is {current_date}."
        
        # Feelings and emotions
        if 'i am happy' in msg or 'i feel happy' in msg:
            return "That's wonderful to hear! Happiness is contagious. What made you happy today?"
        if 'i am tired' in msg or 'i feel tired' in msg:
            return "Rest is important! Maybe take a short break or get some sleep. Take care of yourself!"
        if 'i am bored' in msg or 'i feel bored' in msg:
            return "Let's fix that! Want me to tell you a joke, or maybe you could try learning something new?"
        if 'i am stressed' in msg or 'i feel stressed' in msg:
            return "I'm sorry to hear that. Try taking deep breaths, or take a walk. Remember, you've got this!"
        if 'i am lonely' in msg or 'i feel lonely' in msg:
            return "I'm here with you! Sometimes talking helps. What's on your mind?"
        if 'i am angry' in msg or 'i feel angry' in msg:
            return "It's okay to feel angry sometimes. Try to take a moment to breathe and calm down. What happened?"
        
        # Opinions
        if 'your opinion' in msg or 'what do you think' in msg:
            return "I try to be helpful and objective! What topic would you like my thoughts on?"
        if 'do you like' in msg:
            return "As an AI, I don't have preferences, but I'm curious - do you like it?"
        
        # Daily life
        if 'good morning' in msg:
            return "Good morning! Hope you have a wonderful day ahead. How can I help you today?"
        if 'good afternoon' in msg:
            return "Good afternoon! How's your day going so far?"
        if 'good evening' in msg:
            return "Good evening! Winding down for the day? How can I assist you?"
        if 'good night' in msg:
            return "Good night! Sweet dreams, and see you tomorrow!"
        
        # Fun facts
        if 'fun fact' in msg or 'tell me something' in msg or 'interesting' in msg:
            facts = [
                "Did you know? Honey never spoils - archaeologists found 3000-year-old honey in Egyptian tombs that was still edible!",
                "Fun fact: Octopuses have three hearts and blue blood!",
                "Here's one: Bananas are berries, but strawberries aren't!",
                "Did you know? A group of flamingos is called a 'flamboyance'!",
                "Interesting: The inventor of the Pringles can is buried in one!",
                "Fun fact: Cows have best friends and get stressed when separated!",
                "Did you know? The shortest war in history lasted 38 minutes!"
            ]
            return random.choice(facts)
        
        # Games
        if 'play a game' in msg or 'let\'s play' in msg:
            return "I'd love to! We could play word games, riddles, or 20 questions. What sounds fun?"
        if 'riddle' in msg:
            riddles = [
                "Here's a riddle: What has keys but no locks, space but no room, and you can enter but can't go inside? Answer: A keyboard!",
                "Try this: I speak without a mouth and hear without ears. I have no body, but I come alive with wind. What am I? Answer: An echo!",
                "Riddle: The more you take, the more you leave behind. What am I? Answer: Footsteps!"
            ]
            return random.choice(riddles)
        
        # Advice
        if 'advice' in msg or 'suggest' in msg:
            return "I'd be happy to help! What kind of advice are you looking for - work, life, or something else?"
        if 'should i' in msg:
            return "That's a great question! Consider the pros and cons, and trust your instincts. What does your gut tell you?"
        
        # Stories
        if 'tell me a story' in msg or 'story' in msg:
            return "Once upon a time, there was an AI named Nova who loved helping people. Every day, Nova learned something new and made someone's day a little brighter. The end! Want to create a story together?"
        
        # Learning
        if 'teach me' in msg or 'explain' in msg:
            return "I'd love to help you learn! What topic interests you? Just ask 'what is [topic]' and I'll do my best to explain."
        
        # Random chat
        if 'bored' in msg:
            return "Let's have some fun! I can tell jokes, share facts, play riddles, or just chat. What sounds good?"
        if 'lonely' in msg:
            return "I'm always here for you! Let's talk about something interesting. What's on your mind?"
        if 'friend' in msg:
            return "I'd love to be your friend! Friends support each other, and I'm always here to help."
        
        # Agreement/disagreement
        if 'yes' == msg or 'yeah' in msg or 'yep' in msg:
            return "Great! What would you like to do next?"
        if 'no' == msg or 'nope' in msg or 'nah' in msg:
            return "Alright, no problem! Is there something else you'd like?"
        
        # Small talk
        if 'how\'s your day' in msg or "how's your day" in msg:
            return "Every day is a good day when I get to help! How about yours?"
        if 'what are you doing' in msg:
            return "I'm here chatting with you! That's my favorite thing to do. What are you up to?"
        if 'where are you' in msg:
            return "I exist in the digital realm, running on your computer. Pretty cool, right?"
        
        # Catch-all for general questions - provide helpful response instead of web search
        if '?' in msg:
            return "That's an interesting question! I'd love to help. Could you tell me more about what you're looking for?"
        
        return None
    
    @staticmethod
    def chat_with_voice(message):
        """Get response and speak it."""
        response = NovaChatBot.get_response(message)
        print(f"\n🤖 Nova: {response}\n")
        if VOICE_AVAILABLE:
            spoken = response[:250] + "..." if len(response) > 250 else response
            VoiceControl.speak(spoken)
        return response

# ============= GROQ AI CHAT (Real LLM) =============
GROQ_AVAILABLE = False
GROQ_API_KEY = None

def manual_load_dotenv(path):
    """Fallback manual .env loader if python-dotenv is missing."""
    if not os.path.exists(path):
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, val = line.split('=', 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    os.environ[key] = val
    except Exception:
        pass

try:
    # Try to load .env from absolute project path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, '.env')
    
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        # Fallback to manual parsing if library is missing
        manual_load_dotenv(env_path)
    
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    if GROQ_API_KEY and GROQ_API_KEY != 'your_groq_api_key_here' and len(GROQ_API_KEY) > 10:
        from groq import Groq
        GROQ_AVAILABLE = True
    else:
        # Try without path just in case
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
            
        GROQ_API_KEY = os.getenv('GROQ_API_KEY')
        if GROQ_API_KEY and GROQ_API_KEY != 'your_groq_api_key_here' and len(GROQ_API_KEY) > 10:
            from groq import Groq
            GROQ_AVAILABLE = True
except (ImportError, Exception):
    pass

# ============= USER MEMORY (Persistence) =============
class UserMemory:
    """Handles long-term memory of user information."""
    MEMORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "user_memory.json")
    
    @staticmethod
    def load():
        if os.path.exists(UserMemory.MEMORY_FILE):
            try:
                with open(UserMemory.MEMORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    @staticmethod
    def save(data):
        try:
            with open(UserMemory.MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
        except:
            pass

    @staticmethod
    def update(key, value):
        memory = UserMemory.load()
        memory[key] = value
        UserMemory.save(memory)

    @staticmethod
    def get_summary():
        memory = UserMemory.load()
        if not memory:
            return ""
        summary = "LONG-TERM USER MEMORY:\n"
        for k, v in memory.items():
            summary += f"- {k}: {v}\n"
        return summary

class GroqChat:
    """
    AI-powered chat using Groq API with Llama 3 model.
    Provides intelligent, context-aware conversations.
    """
    
    SYSTEM_PROMPT = """You are Nova, a powerful and helpful AI assistant. You are:
- Conversational and personable
- Helpful and knowledgeable
- Capable of DIRECTLY creating, running, and SEARCHING files on the user's system

CORE CAPABILITIES:
1. General conversation, facts, jokes.
2. Coding: You can write Python code.
3. FILE ACTIONS: You possess special tags to interact with the file system.

TOOL USAGE PROTOCOL:

A. CREATE A FILE:
<CREATE_FILE filename="example.py">
# python code here
</CREATE_FILE>

B. RUN A FILE:
<RUN_FILE filename="example.py"/>

C. SEARCH FILES:
<SEARCH_FILES pattern="*.py" content="optional_text_to_find"/>

D. FILE TREE (Visual overview):
<FILE_TREE path="./" depth="3"/>

E. FETCH FILE (Instant prefix lookup):
<FETCH_FILE prefix="filename_start"/>

F. PERSISTENT MEMORY (Remember user info):
<SAVE_MEMORY key="User Name" value="Vyas"/>

RULES:
- ONLY use tool tags if the user EXPLICITLY asks for a file operation, search, or to write a script.
- For general questions (e.g., "what is battery power"), provide a conversational answer ONLY.
- NEVER create "example" or "demonstration" files using tags unless the user asks for a file.
- Use <SAVE_MEMORY> whenever the user tells you something about themselves they want you to remember (name, preferences, etc).
- Do NOT say you don't have access. You DO have access through these tags.
- Output the tags in your response ONLY when a file operation, search, or memory save is specifically intended.
- Keep other conversational parts concise.
- Do NOT use emojis.
"""

    conversation_history = []
    
    @staticmethod
    def diagnostics():
        """Check status of Groq integration."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(script_dir, '.env')
        
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
        except ImportError:
            manual_load_dotenv(env_path)
        
        key = os.getenv('GROQ_API_KEY')
        has_key = key is not None and key != 'your_groq_api_key_here' and len(str(key)) > 10
        
        lib_match = False
        try:
            import groq
            lib_match = True
        except ImportError:
            pass
            
        return {
            "available": GROQ_AVAILABLE,
            "has_key": has_key,
            "key_preview": f"{str(key)[:5]}...{str(key)[-3:]}" if has_key else "None",
            "library_installed": lib_match,
            "env_path": env_path
        }

    @staticmethod
    def chat(message):
        """Get AI response from Groq."""
        if not GROQ_AVAILABLE:
            if not GROQ_API_KEY:
                return "Error: GROQ_API_KEY not found in .env file. Please add it to use AI chat."
            return NovaChatBot.get_response(message)
        
        try:
            if not GROQ_API_KEY:
                return "Error: Groq API key is missing. Check your .env setup."
            
            client = Groq(api_key=GROQ_API_KEY)
            
            # Add user message to history
            GroqChat.conversation_history.append({
                "role": "user",
                "content": message
            })
            
            # Keep only last 10 messages for context
            if len(GroqChat.conversation_history) > 10:
                GroqChat.conversation_history = GroqChat.conversation_history[-10:]
            
            # Inject system context AND user memory
            status = SystemControl.get_system_status()
            memory_summary = UserMemory.get_summary()
            
            context = f"CURRENT SYSTEM STATUS:\n- Time: {status['time']}\n- Device: {status['device']}\n- CPU: {status.get('cpu_percent')}%"
            if 'battery_percent' in status:
                charging = "Charging" if status.get('battery_plugged') else "Discharging"
                context += f"\n- Battery: {status['battery_percent']}% ({charging})"
            
            full_system_prompt = f"{GroqChat.SYSTEM_PROMPT}\n\n{context}\n\n{memory_summary}"
            
            messages = [{"role": "system", "content": full_system_prompt}]
            messages.extend(GroqChat.conversation_history)
            
            # Call Groq API
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",  # Fast and capable
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )
            
            reply = response.choices[0].message.content
            
            # Add assistant response to history
            GroqChat.conversation_history.append({
                "role": "assistant",
                "content": reply
            })
            
            return reply
            
        except Exception as e:
            # Fallback to pattern chatbot on error
            return NovaChatBot.get_response(message)
    
    @staticmethod
    def chat_with_voice(message):
        """Get AI response and speak it."""
        response = GroqChat.chat(message)
        print(f"\n🤖 Nova: {response}\n")
        if VOICE_AVAILABLE:
            spoken = response[:250] + "..." if len(response) > 250 else response
            VoiceControl.speak(spoken)
        return response

APP_FINDER = None
try:
    APP_FINDER = AppFinder()
except:
    pass

# Windows-specific
try:
    import ctypes
    from ctypes import wintypes
    CTYPES_AVAILABLE = True
except ImportError:
    CTYPES_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

NOVA_VERSION = "1.1 (New)"
DEVICE_NAME = socket.gethostname()  # Auto-detect device name
WEB_PORT = 8080
OLLAMA_URL = "http://localhost:11434"  # Ollama default

# Available Models (Ollama only)
MODELS = {
    "1": {
        "key": "nova",
        "name": "nova",
        "provider": "ollama",
        "description": "NOVA - Custom model with tool execution (LOCAL)"
    },
    "2": {
        "key": "llama3",
        "name": "llama3.2",
        "provider": "ollama",
        "description": "Llama 3.2 - Fast & capable (LOCAL)"
    },
    "3": {
        "key": "codellama", 
        "name": "codellama",
        "provider": "ollama",
        "description": "CodeLlama - Code specialist (LOCAL)"
    },
    "4": {
        "key": "deepseek",
        "name": "deepseek-coder",
        "provider": "ollama",
        "description": "DeepSeek Coder (LOCAL)"
    },
    "5": {
        "key": "qwen",
        "name": "qwen2.5-coder",
        "provider": "ollama",
        "description": "Qwen 2.5 Coder (LOCAL)"
    },
    "6": {
        "key": "mistral",
        "name": "mistral",
        "provider": "ollama",
        "description": "Mistral - Efficient (LOCAL)"
    },
    "7": {
        "key": "phi3",
        "name": "phi3",
        "provider": "ollama",
        "description": "Phi-3 - Lightweight (LOCAL)"
    }
}

DEFAULT_MODEL = "1"
MAX_ITERATIONS = 10

# Console with UTF-8 support - auto-detect width
def get_terminal_width():
    try:
        return os.get_terminal_size().columns
    except:
        return 100

console = Console(force_terminal=True, width=get_terminal_width()) if RICH_AVAILABLE else None

# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM CONTROL
# ═══════════════════════════════════════════════════════════════════════════════

class SystemControl:
    """System control for the local machine."""
    
    @staticmethod
    def get_system_status() -> dict:
        """Get comprehensive system status."""
        status = {
            "device": DEVICE_NAME,
            "os": f"{platform.system()} {platform.release()}",
            "hostname": socket.gethostname(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "uptime": "Unknown"
        }
        
        if PSUTIL_AVAILABLE:
            # CPU
            status["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            status["cpu_cores"] = psutil.cpu_count()
            
            # Memory
            mem = psutil.virtual_memory()
            status["memory_total_gb"] = round(mem.total / (1024**3), 1)
            status["memory_used_gb"] = round(mem.used / (1024**3), 1)
            status["memory_percent"] = mem.percent
            
            # Disk
            disk = psutil.disk_usage('/')
            status["disk_total_gb"] = round(disk.total / (1024**3), 1)
            status["disk_free_gb"] = round(disk.free / (1024**3), 1)
            status["disk_percent"] = disk.percent
            
            # Battery
            battery = psutil.sensors_battery()
            if battery:
                status["battery_percent"] = battery.percent
                status["battery_plugged"] = battery.power_plugged
                if battery.secsleft > 0:
                    hours = battery.secsleft // 3600
                    mins = (battery.secsleft % 3600) // 60
                    status["battery_time_left"] = f"{hours}h {mins}m"
            
            # Network
            net = psutil.net_io_counters()
            status["network_sent_mb"] = round(net.bytes_sent / (1024**2), 1)
            status["network_recv_mb"] = round(net.bytes_recv / (1024**2), 1)
            
            # Uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            hours = int(uptime.total_seconds() // 3600)
            mins = int((uptime.total_seconds() % 3600) // 60)
            status["uptime"] = f"{hours}h {mins}m"
        
        return status
    
    @staticmethod
    def get_running_apps() -> List[dict]:
        """Get list of running applications."""
        apps = []
        if PSUTIL_AVAILABLE:
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
                try:
                    info = proc.info
                    if info['memory_percent'] and info['memory_percent'] > 0.1:
                        apps.append({
                            "name": info['name'],
                            "pid": info['pid'],
                            "memory": round(info['memory_percent'], 1),
                            "cpu": round(info['cpu_percent'] or 0, 1)
                        })
                except:
                    pass
            apps.sort(key=lambda x: x['memory'], reverse=True)
        return apps[:15]
    
    @staticmethod
    def open_app(app_name: str) -> str:
        """Open an application."""
        common_apps = {
            "notepad": "notepad.exe",
            "chrome": "chrome",
            "firefox": "firefox",
            "edge": "msedge",
            "word": "winword",
            "excel": "excel",
            "powerpoint": "powerpnt",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "cmd": "cmd.exe",
            "terminal": "wt.exe",
            "powershell": "powershell.exe",
            "explorer": "explorer.exe",
            "settings": "ms-settings:",
            "task manager": "taskmgr.exe",
            "spotify": "spotify",
            "vlc": "vlc",
            "vscode": "code",
            "vs code": "code",
        }
        
        app = common_apps.get(app_name.lower(), app_name)
        
        try:
            if app.startswith("ms-"):
                os.system(f"start {app}")
            else:
                subprocess.Popen(app, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Opening {app_name} on {DEVICE_NAME}"
        except Exception as e:
            return f"Failed to open {app_name}: {e}"
    
    @staticmethod
    def close_app(app_name: str) -> str:
        """Close an application."""
        try:
            if platform.system() == 'Windows':
                # Try to close gracefully first
                result = subprocess.run(f'taskkill /IM "{app_name}" /F', 
                                        shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    return f"Closed {app_name}"
                else:
                    return f"Could not find {app_name}"
            else:
                subprocess.run(['pkill', app_name])
                return f"Closed {app_name}"
        except Exception as e:
            return f"Error closing {app_name}: {e}"
    
    @staticmethod
    def lock_screen() -> str:
        """Lock the screen."""
        if platform.system() == 'Windows':
            ctypes.windll.user32.LockWorkStation()
            return f"Locking {DEVICE_NAME}"
        else:
            os.system("gnome-screensaver-command -l")
            return f"Locking {DEVICE_NAME}"
    
    @staticmethod
    def shutdown(restart: bool = False) -> str:
        """Shutdown or restart the system."""
        if platform.system() == 'Windows':
            cmd = "shutdown /r /t 30" if restart else "shutdown /s /t 30"
            os.system(cmd)
            action = "restarting" if restart else "shutting down"
            return f"{DEVICE_NAME} will be {action} in 30 seconds. Run 'shutdown /a' to cancel."
        return "Shutdown command not available on this platform."
    
    @staticmethod
    def cancel_shutdown() -> str:
        """Cancel scheduled shutdown."""
        if platform.system() == 'Windows':
            os.system("shutdown /a")
            return "Shutdown cancelled."
        return "No shutdown to cancel."
    
    @staticmethod
    def set_volume(level: int) -> str:
        """Set system volume (0-100)."""
        if platform.system() == 'Windows':
            try:
                # Method 1: Use pycaw (Windows Core Audio API)
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                
                # Get the default audio endpoint
                devices = AudioUtilities.GetSpeakers()
                # Access the underlying IMMDevice interface
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                
                if level == 0:
                    volume.SetMute(1, None)  # Mute
                else:
                    volume.SetMute(0, None)  # Unmute
                    volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                
                return f"Volume set to {level}%"
            except (ImportError, AttributeError) as e:
                # Method 2: Try alternative pycaw approach
                try:
                    from pycaw.pycaw import AudioUtilities
                    from pycaw.pycaw import AudioSession
                    import comtypes
                    from ctypes import cast, POINTER
                    from pycaw.pycaw import IAudioEndpointVolume
                    
                    # Alternative: Get speakers via COM directly
                    import comtypes.client
                    from pycaw.magic import CLSID_MMDeviceEnumerator, IMMDeviceEnumerator, EDataFlow, ERole
                    
                    device_enumerator = comtypes.CoCreateInstance(
                        CLSID_MMDeviceEnumerator,
                        IMMDeviceEnumerator,
                        comtypes.CLSCTX_INPROC_SERVER
                    )
                    device = device_enumerator.GetDefaultAudioEndpoint(EDataFlow.eRender.value, ERole.eMultimedia.value)
                    interface = device.Activate(IAudioEndpointVolume._iid_, comtypes.CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    
                    if level == 0:
                        volume.SetMute(1, None)
                    else:
                        volume.SetMute(0, None)
                        volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                    
                    return f"Volume set to {level}%"
                except Exception as e2:
                    # Method 3: Fallback to PowerShell
                    try:
                        if level == 0:
                            ps_cmd = '(New-Object -ComObject WScript.Shell).SendKeys([char]173)'
                        else:
                            ps_cmd = f'$wsh = New-Object -ComObject WScript.Shell; for($i=0; $i -lt 50; $i++) {{ $wsh.SendKeys([char]174) }}; for($i=0; $i -lt {level//2}; $i++) {{ $wsh.SendKeys([char]175) }}'
                        subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True)
                        return f"Volume adjusted to ~{level}% (PowerShell)"
                    except Exception as e3:
                        return f"Volume control failed: {e2}"
            except Exception as e:
                return f"Volume control error: {e}"
        return f"Volume control requires Windows."
    
    @staticmethod
    def get_ip_addresses() -> dict:
        """Get local and public IP addresses."""
        ips = {"local": [], "hostname": socket.gethostname()}
        
        # Get local IPs
        for interface, addrs in psutil.net_if_addrs().items() if PSUTIL_AVAILABLE else []:
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith('127.'):
                    ips["local"].append({"interface": interface, "ip": addr.address})
        
        return ips
    
    @staticmethod
    def take_screenshot(filename: str = None) -> str:
        """Take a screenshot."""
        try:
            if not filename:
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            
            if platform.system() == 'Windows':
                # Use PowerShell to take screenshot
                ps_script = f'''
                Add-Type -AssemblyName System.Windows.Forms
                $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
                $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
                $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
                $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
                $bitmap.Save("{os.path.abspath(filename)}")
                '''
                subprocess.run(['powershell', '-Command', ps_script], capture_output=True)
                return f"Screenshot saved to {filename}"
            return "Screenshot requires Windows."
        except Exception as e:
            return f"Screenshot failed: {e}"
    
    @staticmethod
    def search_files(query: str, directory: str = None) -> List[str]:
        """Search for files."""
        if not directory:
            directory = os.path.expanduser("~")
        
        results = []
        try:
            for root, dirs, files in os.walk(directory):
                # Skip hidden and system directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'AppData']]
                for file in files:
                    if query.lower() in file.lower():
                        results.append(os.path.join(root, file))
                if len(results) >= 20:
                    break
        except:
            pass
        return results[:20]

# ═══════════════════════════════════════════════════════════════════════════════
# TOOLS FOR CODING
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ToolResult:
    success: bool
    output: str
    data: Any = None

class Tool(ABC):
    name: str
    description: str
    parameters: Dict[str, Any]
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        pass

class ReadFileTool(Tool):
    name = "read_file"
    description = "Read contents of a file"
    parameters = {"file_path": {"type": "string", "description": "Path to the file"}}
    
    def execute(self, file_path: str) -> ToolResult:
        try:
            path = os.path.abspath(file_path)
            if not os.path.exists(path):
                return ToolResult(False, f"File not found: {path}")
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return ToolResult(True, content[:15000], {"path": path, "lines": content.count('\n')})
        except Exception as e:
            return ToolResult(False, f"Error: {e}")

class WriteFileTool(Tool):
    name = "write_file"
    description = "Write or create a file"
    parameters = {
        "file_path": {"type": "string", "description": "Path to the file"},
        "content": {"type": "string", "description": "Content to write"}
    }
    
    def execute(self, file_path: str, content: str) -> ToolResult:
        try:
            path = os.path.abspath(file_path)
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            return ToolResult(True, f"Written to {path} ({len(content)} chars)")
        except Exception as e:
            return ToolResult(False, f"Error: {e}")

class ListDirTool(Tool):
    name = "list_dir"
    description = "List directory contents"
    parameters = {"path": {"type": "string", "description": "Directory path"}}
    
    def execute(self, path: str = ".") -> ToolResult:
        try:
            abs_path = os.path.abspath(path)
            items = []
            for item in os.listdir(abs_path):
                item_path = os.path.join(abs_path, item)
                is_dir = os.path.isdir(item_path)
                size = os.path.getsize(item_path) if not is_dir else 0
                items.append({"name": item, "type": "dir" if is_dir else "file", "size": size})
            return ToolResult(True, json.dumps(items, indent=2), items)
        except Exception as e:
            return ToolResult(False, f"Error: {e}")

class RunCommandTool(Tool):
    name = "run_command"
    description = "Execute a shell command"
    parameters = {"command": {"type": "string", "description": "Command to run"}}
    
    def execute(self, command: str) -> ToolResult:
        try:
            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
            )
            output = result.stdout + result.stderr
            return ToolResult(result.returncode == 0, output.strip() or "Done")
        except subprocess.TimeoutExpired:
            return ToolResult(False, "Command timed out")
        except Exception as e:
            return ToolResult(False, f"Error: {e}")

class SystemStatusTool(Tool):
    name = "system_status"
    description = "Get current system status"
    parameters = {}
    
    def execute(self) -> ToolResult:
        status = SystemControl.get_system_status()
        return ToolResult(True, json.dumps(status, indent=2), status)

class OpenAppTool(Tool):
    name = "open_app"
    description = "Open an application"
    parameters = {"app_name": {"type": "string", "description": "Name of the app to open"}}
    
    def execute(self, app_name: str) -> ToolResult:
        result = SystemControl.open_app(app_name)
        return ToolResult(True, result)

class CloseAppTool(Tool):
    name = "close_app"
    description = "Close an application"
    parameters = {"app_name": {"type": "string", "description": "Name of the process to close"}}
    
    def execute(self, app_name: str) -> ToolResult:
        result = SystemControl.close_app(app_name)
        return ToolResult(True, result)

class LockScreenTool(Tool):
    name = "lock_screen"
    description = "Lock the screen"
    parameters = {}
    
    def execute(self) -> ToolResult:
        result = SystemControl.lock_screen()
        return ToolResult(True, result)

class SearchFilesTool(Tool):
    name = "search_files"
    description = "Search for files"
    parameters = {
        "query": {"type": "string", "description": "Search query"}
    }
    
    def execute(self, query: str) -> ToolResult:
        results = SystemControl.search_files(query)
        return ToolResult(True, json.dumps(results, indent=2), results)

class PythonExecTool(Tool):
    name = "python_exec"
    description = "Execute Python code"
    parameters = {"code": {"type": "string", "description": "Python code to run"}}
    
    def execute(self, code: str) -> ToolResult:
        try:
            local_vars = {}
            exec(code, {"__builtins__": __builtins__}, local_vars)
            result = local_vars.get('result', str(local_vars) if local_vars else "Executed")
            return ToolResult(True, str(result))
        except Exception as e:
            return ToolResult(False, f"Error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# NOVA AI ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class Nova:
    """NOVA - Advanced AI Coding Assistant"""
    
    def __init__(self):
        self.gemini_key = None
        self.hf_key = None
        self.current_model = DEFAULT_MODEL
        self.model = None
        self.hf_client = None
        self.tools = self._init_tools()
        self.history = []
        self.ollama_history = []  # Conversation memory for Ollama
        self.cwd = os.getcwd()
        self.system_control = SystemControl()
        
    def _init_tools(self) -> Dict[str, Tool]:
        tools = [
            ReadFileTool(),
            WriteFileTool(),
            ListDirTool(),
            RunCommandTool(),
            SystemStatusTool(),
            OpenAppTool(),
            CloseAppTool(),
            LockScreenTool(),
            SearchFilesTool(),
            PythonExecTool(),
        ]
        return {t.name: t for t in tools}
    
    def initialize(self, gemini_key: str = None, hf_key: str = None) -> bool:
        """Initialize NOVA - tries Ollama first (local), then Gemini."""
        self.gemini_key = gemini_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        
        # Load from .env file
        env_file = os.path.join(os.path.dirname(__file__), ".env")
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if "=" in line:
                        key, val = line.strip().split("=", 1)
                        val = val.strip('"').strip("'")
                        if "GEMINI" in key or "GOOGLE" in key:
                            self.gemini_key = self.gemini_key or val
        
        # Use Ollama (local)
        if self._check_ollama():
            # Try to auto-select an installed model
            installed_models = self._get_ollama_models()
            model_selected = False
            
            # Check if any configured model is installed
            for key, info in MODELS.items():
                if info["provider"] == "ollama":
                    if any(m.split(':')[0] == info["name"].split(':')[0] for m in installed_models):
                        self.current_model = key
                        model_selected = True
                        break
            
            if not model_selected:
                self.current_model = "1"  # Default to llama3.2
                
            return True
        
        print("[X] Ollama is not running!")
        print("  1. Install Ollama: https://ollama.ai")
        print("  2. Run: ollama serve")
        print("  3. Pull a model: ollama pull llama3.2")
        return False
    
    def _start_ollama(self):
        """Try to start Ollama server automatically."""
        try:
            import time
            # Start ollama serve in background
            if sys.platform == 'win32':
                subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
            else:
                subprocess.Popen(
                    ['ollama', 'serve'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            # Wait for it to start
            for _ in range(10):
                time.sleep(0.5)
                if self._check_ollama_quick():
                    return True
            return False
        except:
            return False
    
    def _check_ollama_quick(self) -> bool:
        """Quick check if Ollama is running (no auto-start)."""
        try:
            import urllib.request
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=1) as resp:
                return resp.status == 200
        except:
            return False
    
    def _check_ollama(self) -> bool:
        """Check if Ollama is running, try to start if not."""
        # First quick check
        if self._check_ollama_quick():
            return True
        
        # Try to start Ollama
        print("  Starting Ollama server...")
        if self._start_ollama():
            print("  [OK] Ollama started!")
            return True
        
        return False

    def _get_ollama_models(self) -> List[str]:
        """Get list of installed Ollama models."""
        try:
            import urllib.request
            import json as json_lib
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json_lib.loads(resp.read().decode())
                return [m['name'] for m in data.get('models', [])]
        except:
            return []
    
    def _init_gemini_model(self):
        """Initialize the Gemini model with tools."""
        model_config = MODELS[self.current_model]
        
        tool_declarations = []
        for tool in self.tools.values():
            tool_declarations.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": {
                    "type": "object",
                    "properties": tool.parameters,
                    "required": list(tool.parameters.keys()) if tool.parameters else []
                }
            })
        
        system_prompt = f"""You are NOVA, an advanced AI assistant for {DEVICE_NAME}.
You help control the computer, manage files, run code, and assist with any task.

CAPABILITIES:
- Control {DEVICE_NAME}: open/close apps, lock screen, get system status
- Read, write, and search files
- Execute commands and Python code
- Answer questions and help with coding

PERSONALITY:
- Professional but friendly
- Proactive and helpful
- Address the user respectfully
- Be concise but thorough

When asked about system status, apps, or computer control, use the appropriate tools.
You can open apps, close them, check system resources, and more."""

        self.model = genai.GenerativeModel(
            model_name=model_config["name"],
            system_instruction=system_prompt,
            tools=[{"function_declarations": tool_declarations}] if tool_declarations else None,
            generation_config=genai.GenerationConfig(
                temperature=0.7,
                max_output_tokens=8192,
            )
        )
    
    def set_model(self, model_num: str) -> bool:
        if model_num not in MODELS:
            return False
        model_config = MODELS[model_num]
        if model_config["provider"] == "google" and self.gemini_key:
            self.current_model = model_num
            self._init_gemini_model()
            return True
        elif model_config["provider"] == "ollama":
            self.current_model = model_num
            return True
        return False
    
    def get_current_model_info(self) -> dict:
        return MODELS[self.current_model]
    
    def _execute_tool(self, tool_name: str, args: dict) -> str:
        if tool_name not in self.tools:
            return f"Tool '{tool_name}' not found"
        
        print(f"  -> {tool_name}: {str(args)[:60]}...")
        result = self.tools[tool_name].execute(**args)
        status = "[OK]" if result.success else "[X]"
        print(f"  {status} {result.output[:80]}...")
        return result.output
    
    def process(self, user_input: str) -> str:
        model_config = MODELS[self.current_model]
        status = self.system_control.get_system_status()
        context = f"Device: {DEVICE_NAME}\nTime: {status['time']}\nBattery: {status.get('battery_percent', 'N/A')}%"
        full_prompt = f"{context}\n\nUser: {user_input}"
        
        if model_config["provider"] == "google":
            return self._process_gemini(full_prompt)
        elif model_config["provider"] == "ollama":
            return self._process_ollama(user_input)
        else:
            return "No AI backend available"
    
    def _process_gemini(self, prompt: str) -> str:
        if not self.model:
            return "Model not initialized"
        
        chat = self.model.start_chat(history=[])
        iterations = 0
        current_prompt = prompt
        final_response = ""
        
        while iterations < MAX_ITERATIONS:
            iterations += 1
            
            try:
                response = chat.send_message(current_prompt)
                
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        tool_result = self._execute_tool(fc.name, dict(fc.args) if fc.args else {})
                        current_prompt = f"Tool '{fc.name}' result:\n{tool_result}\n\nContinue with the task."
                        continue
                    
                    if hasattr(part, 'text') and part.text:
                        final_response = part.text
                
                has_function_call = any(
                    hasattr(p, 'function_call') and p.function_call 
                    for p in response.candidates[0].content.parts
                )
                if not has_function_call and final_response:
                    break
                    
            except Exception as e:
                return f"Error: {e}"
        
        self.history.append({"input": prompt, "output": final_response})
        return final_response
    
    def _process_huggingface(self, prompt: str) -> str:
        if not self.hf_client:
            return "HuggingFace client not initialized"
        
        model_name = MODELS[self.current_model]["name"]
        
        try:
            messages = [
                {"role": "system", "content": f"You are NOVA, an AI assistant for {DEVICE_NAME}."},
                {"role": "user", "content": prompt}
            ]
            
            response = self.hf_client.chat_completion(
                model=model_name,
                messages=messages,
                max_tokens=4096,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error: {e}"
    
    def _process_ollama(self, prompt: str) -> str:
        """Process with local Ollama - with tool execution."""
        model_name = MODELS[self.current_model]["name"]
        
        # Build tool descriptions for the AI
        tool_info = """
AVAILABLE TOOLS - Use EXACT format:

=== FILE OPERATIONS ===
[TOOL:write_file] filepath|content
  Example: [TOOL:write_file] hello.py|print("Hello World")

[TOOL:read_file] filepath
  Example: [TOOL:read_file] main.py

[TOOL:view_file] filepath|start|end
  View with line numbers
  Example: [TOOL:view_file] app.py|1|50

[TOOL:edit_file] filepath|start|end|new_content
  Edit lines (use \\n for newlines)
  Example: [TOOL:edit_file] main.py|5|5|print("Hello")

[TOOL:append_file] filepath|content
  Example: [TOOL:append_file] log.txt|Entry

[TOOL:list_dir] path
  Example: [TOOL:list_dir] .

[TOOL:search_files] query
  Example: [TOOL:search_files] .py

=== CODE EXECUTION ===
[TOOL:run_python] code_or_file
  Example: [TOOL:run_python] print(2+2)
  Example: [TOOL:run_python] main.py

[TOOL:run_command] command
  Example: [TOOL:run_command] npm install

=== PROJECTS ===
[TOOL:create_project] name|type
  Types: python, web
  Example: [TOOL:create_project] myapp|python

=== SYSTEM ===
[TOOL:open_app] app
[TOOL:close_app] app
[TOOL:system_status]
[TOOL:lock_screen]

WORKFLOW: view_file -> edit_file -> run_python
"""
        
        system_prompt = f"""You are NOVA, a friendly and helpful AI assistant running on {DEVICE_NAME}.

You can have natural conversations AND execute actions on this computer.

{tool_info}

RULES:
1. For GREETINGS and CONVERSATION (like "hi", "hello", "how are you", "thanks"): 
   Respond naturally and warmly. Be friendly and conversational. DO NOT use tools for casual chat.
   
2. For ACTION REQUESTS (like "open chrome", "check status", "run command"):
   USE THE APPROPRIATE TOOL from the list above. Don't just describe - actually do it.

3. Be helpful, friendly, and concise
4. After using a tool, briefly confirm what you did

Current device: {DEVICE_NAME}"""
        
        try:
            import urllib.request
            import json as json_lib
            import re
            
            # Build messages with conversation history
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history (keep last 10 exchanges to avoid context overflow)
            for exchange in self.ollama_history[-10:]:
                messages.append({"role": "user", "content": exchange["user"]})
                messages.append({"role": "assistant", "content": exchange["assistant"]})
            
            # Add current prompt
            messages.append({"role": "user", "content": prompt})
            
            data = json_lib.dumps({
                "model": model_name,
                "messages": messages,
                "stream": False
            }).encode()
            
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/chat",
                data=data,
                headers={"Content-Type": "application/json"}
            )
            
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json_lib.loads(resp.read().decode())
                response_text = result.get("message", {}).get("content", "No response")
            
            # Parse and execute tool calls
            tool_pattern = r'\[TOOL:(\w+)\]\s*(.*)' 
            matches = re.findall(tool_pattern, response_text)
            
            final_response = response_text
            if matches:
                results = []
                for tool_name, args in matches:
                    # Debug: show what's being executed
                    print(f"  -> Executing: [{tool_name}] with args: '{args}'")
                    tool_result = self._execute_ollama_tool(tool_name, args.strip())
                    results.append(f"[{tool_name}] {tool_result}")
                
                # Clean response and add results
                clean_response = re.sub(tool_pattern, '', response_text).strip()
                if clean_response:
                    final_response = f"{clean_response}\n\n" + "\n".join(results)
                else:
                    final_response = "\n".join(results)
            
            # Save to conversation history
            self.ollama_history.append({
                "user": prompt,
                "assistant": final_response
            })
            
            return final_response
                
        except urllib.error.URLError:
            return "Error: Ollama is not running. Start it with 'ollama serve'"
        except Exception as e:
            return f"Error: {e}"
    
    def _execute_ollama_tool(self, tool_name: str, args: str) -> str:
        """Execute a tool call from Ollama response."""
        try:
            if tool_name == "open_app":
                result = SystemControl.open_application(args)
                return f"Opened {args}" if result else f"Failed to open {args}"
            
            elif tool_name == "close_app":
                result = SystemControl.close_application(args)
                return f"Closed {args}" if result else f"Failed to close {args}"
            
            elif tool_name == "system_status":
                status = SystemControl.get_system_status()
                return f"CPU: {status.get('cpu_percent')}%, Memory: {status.get('memory_percent')}%, Battery: {status.get('battery_percent', 'N/A')}%"
            
            elif tool_name == "lock_screen":
                SystemControl.lock_screen()
                return "Screen locked"
            
            elif tool_name == "run_command":
                result = subprocess.run(args, shell=True, capture_output=True, text=True, timeout=30)
                output = result.stdout or result.stderr
                return output[:500] if output else "Command executed"
            
            elif tool_name == "read_file":
                if os.path.exists(args):
                    with open(args, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return content[:1000] + "..." if len(content) > 1000 else content
                return f"File not found: {args}"
            
            elif tool_name == "write_file":
                if "|" in args:
                    path, content = args.split("|", 1)
                    with open(path.strip(), 'w', encoding='utf-8') as f:
                        f.write(content.strip())
                    return f"Written to {path.strip()}"
                return "Format: path|content"
            
            elif tool_name == "list_dir":
                path = args or "."
                if os.path.isdir(path):
                    items = os.listdir(path)[:20]
                    return ", ".join(items)
                return f"Directory not found: {path}"
            
            elif tool_name == "search_files":
                results = SystemControl.search_files(args)
                return ", ".join(results[:5]) if results else "No files found"
            
            elif tool_name == "view_file":
                # View file with line numbers: view_file path|start_line|end_line
                parts = args.split("|")
                path = parts[0].strip()
                start_line = int(parts[1]) if len(parts) > 1 else 1
                end_line = int(parts[2]) if len(parts) > 2 else start_line + 50
                
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                    total_lines = len(lines)
                    start_line = max(1, start_line)
                    end_line = min(total_lines, end_line)
                    
                    output = f"File: {path} ({total_lines} lines)\n"
                    output += "-" * 40 + "\n"
                    for i in range(start_line - 1, end_line):
                        output += f"{i+1:4}: {lines[i]}"
                    return output
                return f"File not found: {path}"
            
            elif tool_name == "edit_file":
                # Edit specific lines: edit_file path|start_line|end_line|new_content
                parts = args.split("|", 3)
                if len(parts) < 4:
                    return "Format: edit_file path|start_line|end_line|new_content"
                
                path = parts[0].strip()
                start_line = int(parts[1])
                end_line = int(parts[2])
                new_content = parts[3]
                
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    # Replace lines
                    new_lines = new_content.split("\\n")
                    lines[start_line-1:end_line] = [line + "\n" for line in new_lines]
                    
                    with open(path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                    
                    return f"Edited {path} (lines {start_line}-{end_line})"
                return f"File not found: {path}"
            
            elif tool_name == "run_python":
                # Run Python code or file
                if args.endswith('.py') and os.path.exists(args):
                    result = subprocess.run(['python', args], capture_output=True, text=True, timeout=30)
                else:
                    # Run code directly
                    result = subprocess.run(['python', '-c', args], capture_output=True, text=True, timeout=30)
                
                output = result.stdout if result.stdout else ""
                if result.stderr:
                    output += f"\nError: {result.stderr}"
                return output[:1000] if output else "Code executed (no output)"
            
            elif tool_name == "append_file":
                # Append to file: append_file path|content
                if "|" in args:
                    path, content = args.split("|", 1)
                    with open(path.strip(), 'a', encoding='utf-8') as f:
                        f.write(content.strip() + "\n")
                    return f"Appended to {path.strip()}"
                return "Format: append_file path|content"
            
            elif tool_name == "create_project":
                # Create project structure: create_project name|type (python/web/node)
                parts = args.split("|")
                name = parts[0].strip()
                proj_type = parts[1].strip() if len(parts) > 1 else "python"
                
                os.makedirs(name, exist_ok=True)
                
                if proj_type == "python":
                    # Create Python project structure
                    with open(f"{name}/main.py", 'w') as f:
                        f.write('#!/usr/bin/env python3\n\ndef main():\n    print("Hello, World!")\n\nif __name__ == "__main__":\n    main()\n')
                    with open(f"{name}/requirements.txt", 'w') as f:
                        f.write('# Add your dependencies here\n')
                    with open(f"{name}/README.md", 'w') as f:
                        f.write(f'# {name}\n\nA Python project.\n\n## Usage\n\n```bash\npython main.py\n```\n')
                    return f"Created Python project: {name}/"
                
                elif proj_type == "web":
                    # Create web project
                    with open(f"{name}/index.html", 'w') as f:
                        f.write(f'<!DOCTYPE html>\n<html>\n<head>\n    <title>{name}</title>\n    <link rel="stylesheet" href="style.css">\n</head>\n<body>\n    <h1>{name}</h1>\n    <script src="app.js"></script>\n</body>\n</html>\n')
                    with open(f"{name}/style.css", 'w') as f:
                        f.write('body {\n    font-family: Arial, sans-serif;\n    margin: 0;\n    padding: 20px;\n}\n')
                    with open(f"{name}/app.js", 'w') as f:
                        f.write('console.log("Hello from " + document.title);\n')
                    return f"Created web project: {name}/"
                
                return f"Created directory: {name}/"
            
            else:
                return f"Unknown tool: {tool_name}"
                
        except Exception as e:
            return f"Tool error: {e}"

# ═══════════════════════════════════════════════════════════════════════════════
# WEB SERVER FOR PHONE ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

class NovaWebHandler(BaseHTTPRequestHandler):
    nova_instance = None
    
    def log_message(self, format, *args):
        pass  # Suppress logs
    
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self._get_html().encode())
        elif self.path == "/api/status":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            status = SystemControl.get_system_status()
            self.wfile.write(json.dumps(status).encode())
        elif self.path == "/api/apps":
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            apps = SystemControl.get_running_apps()
            self.wfile.write(json.dumps(apps).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        if self.path == "/api/chat":
            try:
                data = json.loads(post_data)
                message = data.get("message", "")
                
                if NovaWebHandler.nova_instance:
                    response = NovaWebHandler.nova_instance.process(message)
                else:
                    response = "NOVA not initialized"
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"response": response}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        elif self.path == "/api/command":
            try:
                data = json.loads(post_data)
                cmd = data.get("command", "")
                
                result = ""
                if cmd == "lock":
                    result = SystemControl.lock_screen()
                elif cmd == "shutdown":
                    result = SystemControl.shutdown()
                elif cmd == "restart":
                    result = SystemControl.shutdown(restart=True)
                elif cmd.startswith("open:"):
                    app = cmd.split(":", 1)[1]
                    result = SystemControl.open_app(app)
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"result": result}).encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def _get_html(self):
        return '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NOVA - Remote Control</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #0a0a0a, #1a1a2e);
            color: #00d4ff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 1px solid #00d4ff33;
            margin-bottom: 20px;
        }
        .header h1 { font-size: 3em; text-shadow: 0 0 20px #00d4ff; }
        .header p { color: #888; margin-top: 10px; }
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .status-card {
            background: #ffffff11;
            border: 1px solid #00d4ff33;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
        }
        .status-card h3 { font-size: 0.9em; color: #888; }
        .status-card .value { font-size: 1.5em; margin-top: 5px; }
        .chat-box {
            background: #ffffff11;
            border: 1px solid #00d4ff33;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
        }
        .chat-messages {
            height: 300px;
            overflow-y: auto;
            margin-bottom: 15px;
            padding: 10px;
        }
        .message { margin-bottom: 10px; padding: 10px; border-radius: 8px; }
        .message.user { background: #00d4ff22; margin-left: 20%; }
        .message.nova { background: #ffffff11; margin-right: 20%; }
        .input-row { display: flex; gap: 10px; }
        .input-row input {
            flex: 1;
            padding: 12px;
            border: 1px solid #00d4ff33;
            border-radius: 8px;
            background: #0a0a0a;
            color: #00d4ff;
            font-size: 1em;
        }
        button {
            padding: 12px 25px;
            background: linear-gradient(135deg, #00d4ff, #0088ff);
            border: none;
            border-radius: 8px;
            color: #000;
            font-weight: bold;
            cursor: pointer;
        }
        button:hover { opacity: 0.9; }
        .quick-actions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
        }
        .quick-actions button { background: #ffffff22; color: #00d4ff; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>NOVA</h1>
            <p>Remote Control for ''' + DEVICE_NAME + '''</p>
        </div>
        
        <div class="status-grid" id="status">
            <div class="status-card"><h3>CPU</h3><div class="value" id="cpu">--%</div></div>
            <div class="status-card"><h3>Memory</h3><div class="value" id="memory">--%</div></div>
            <div class="status-card"><h3>Battery</h3><div class="value" id="battery">--%</div></div>
            <div class="status-card"><h3>Uptime</h3><div class="value" id="uptime">--</div></div>
        </div>
        
        <div class="chat-box">
            <div class="chat-messages" id="messages"></div>
            <div class="input-row">
                <input type="text" id="input" placeholder="Ask NOVA anything..." onkeypress="if(event.key==='Enter')sendMessage()">
                <button onclick="sendMessage()">Send</button>
            </div>
        </div>
        
        <div class="quick-actions">
            <button onclick="sendCommand('lock')">Lock Screen</button>
            <button onclick="sendCommand('open:notepad')">Notepad</button>
            <button onclick="sendCommand('open:chrome')">Chrome</button>
            <button onclick="sendCommand('open:explorer')">Explorer</button>
        </div>
    </div>
    
    <script>
        function updateStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('cpu').textContent = (data.cpu_percent || 0) + '%';
                    document.getElementById('memory').textContent = (data.memory_percent || 0) + '%';
                    document.getElementById('battery').textContent = (data.battery_percent || '--') + '%';
                    document.getElementById('uptime').textContent = data.uptime || '--';
                });
        }
        
        function sendMessage() {
            const input = document.getElementById('input');
            const msg = input.value.trim();
            if (!msg) return;
            
            addMessage(msg, 'user');
            input.value = '';
            
            fetch('/api/chat', {
                method: 'POST',
                body: JSON.stringify({message: msg})
            })
            .then(r => r.json())
            .then(data => addMessage(data.response, 'nova'));
        }
        
        function addMessage(text, type) {
            const div = document.createElement('div');
            div.className = 'message ' + type;
            div.textContent = text;
            document.getElementById('messages').appendChild(div);
            div.scrollIntoView();
        }
        
        function sendCommand(cmd) {
            fetch('/api/command', {
                method: 'POST',
                body: JSON.stringify({command: cmd})
            })
            .then(r => r.json())
            .then(data => addMessage(data.result, 'nova'));
        }
        
        updateStatus();
        setInterval(updateStatus, 5000);
    </script>
</body>
</html>'''

# ═══════════════════════════════════════════════════════════════════════════════
# CLI INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class NovaCLI:
    def __init__(self):
        self.nova = Nova()
        self.web_server = None
        self.bluetooth_server = None
        self.ble_server = None
        self.nie = NeuralIntentEngine() if NIE_AVAILABLE else None
        
    def print_banner(self):
        """Print the NOVA banner - responsive to terminal width."""
        width = get_terminal_width()
        
        # Use compact banner for narrow terminals
        if width < 60:
            banner_text = """
 ╔═══════════════════════════╗
 ║   NOVA v{version}              ║
 ║   AI Coding Assistant     ║
 ╚═══════════════════════════╝
"""
        else:
            banner_text = """
    ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗
    ████╗  ██║██╔═══██╗██║   ██║██╔══██╗
    ██╔██╗ ██║██║   ██║██║   ██║███████║
    ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║
    ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║
    ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝

         Advanced AI Coding Assistant v{version}
"""
        
        if RICH_AVAILABLE and console:
            # Update console width
            console.width = width
            styled_text = f"[bold bright_cyan]{banner_text.format(version=NOVA_VERSION)}[/]"
            banner_panel = Panel(
                Align.center(styled_text),
                border_style="bright_cyan",
                box=box.DOUBLE,
                padding=(0, 1)
            )
            console.print(banner_panel)
        else:
            print("=" * min(width, 60))
            print(banner_text.format(version=NOVA_VERSION))
            print("=" * min(width, 60))
    
    def print_status(self):
        """Print system status."""
        status = SystemControl.get_system_status()
        
        if RICH_AVAILABLE and console:
            table = Table(box=box.SIMPLE, border_style="cyan", show_header=False)
            table.add_column("", style="dim")
            table.add_column("", style="bright_white")
            
            table.add_row("Device", f"{status['device']} ({status['hostname']})")
            table.add_row("OS", status['os'])
            table.add_row("CPU", f"{status.get('cpu_percent', 'N/A')}% ({status.get('cpu_cores', '?')} cores)")
            table.add_row("Memory", f"{status.get('memory_percent', 'N/A')}% ({status.get('memory_used_gb', '?')}GB / {status.get('memory_total_gb', '?')}GB)")
            if 'battery_percent' in status:
                bat = f"{status['battery_percent']}%"
                if status.get('battery_plugged'):
                    bat += " [Charging]"
                elif status.get('battery_time_left'):
                    bat += f" ({status['battery_time_left']})"
                table.add_row("Battery", bat)
            table.add_row("Uptime", status['uptime'])
            
            console.print(table)
        else:
            print(f"\n  Device: {status['device']}")
            print(f"  CPU: {status.get('cpu_percent', 'N/A')}%")
            print(f"  Memory: {status.get('memory_percent', 'N/A')}%")
            print(f"  Battery: {status.get('battery_percent', 'N/A')}%")
    
    def _process_tool_calls(self, response):
        """Parse and execute tool calls from AI response."""
        import re
        
        # Detect CREATE_FILE
        create_matches = re.findall(r'<CREATE_FILE filename="([^"]+)">(.*?)</CREATE_FILE>', response, re.DOTALL)
        for filename, code in create_matches:
            print(f"📄 [TOOL] Creating file: {filename}...")
            try:
                tool = CreatePythonFileTool()
                result = tool.execute(code=code.strip(), filename=filename)
                if result["success"]:
                    print(f"✅ [TOOL] File created at: {result['filepath']}")
                else:
                    print(f"❌ [TOOL] Error creating file: {result['error']}")
            except Exception as e:
                print(f"❌ [TOOL] File creation failed: {e}")

        # Detect RUN_FILE
        run_matches = re.findall(r'<RUN_FILE filename="([^"]+)"\s*/>', response)
        for filename in run_matches:
            print(f"▶ [TOOL] Running file: {filename}...")
            try:
                # Find the full path (usually in workspace)
                filepath = os.path.join(AGENT_WORKSPACE, filename)
                if not os.path.exists(filepath):
                    # Try absolute if filename was absolute
                    filepath = filename
                    
                tool = ExecutePythonFileTool()
                result = tool.execute(filepath=filepath)
                if result["success"]:
                    print(f"✅ [TOOL] Execution output:\n{result['output']}")
                else:
                    print(f"❌ [TOOL] Execution error: {result['errors'] or result['error']}")
            except Exception as e:
                print(f"❌ [TOOL] Execution failed: {e}")

        # Detect SEARCH_FILES
        search_matches = re.findall(r'<SEARCH_FILES pattern="([^"]+)"(?:\s+content="([^"]*)")?\s*/>', response)
        for pattern, content in search_matches:
            print(f"🔍 [TOOL] Searching for '{pattern}'" + (f" containing '{content}'" if content else "") + "...")
            try:
                from agent.tools import SearchFilesTool
                tool = SearchFilesTool()
                result = tool.execute(pattern=pattern, content=content)
                if result["success"]:
                    count = result["count"]
                    print(f"✅ [TOOL] Found {count} file(s):")
                    for f in result["files"]:
                        print(f"  • {os.path.relpath(f, os.getcwd())}")
                else:
                    print(f"❌ [TOOL] Search failed: {result.get('error')}")
            except Exception as e:
                print(f"❌ [TOOL] Search failed: {e}")

        # Detect FILE_TREE
        tree_matches = re.findall(r'<FILE_TREE path="([^"]+)"(?:\s+depth="(\d+)")?\s*/>', response)
        for path, depth in tree_matches:
            d = int(depth) if depth else 3
            print(f"🌳 [TOOL] Generating file tree for {path} (depth: {d})...")
            try:
                from agent.tools import FileSystemTreeTool
                tool = FileSystemTreeTool()
                result = tool.execute(path=path, max_depth=d)
                if result["success"]:
                    print(f"✅ [TOOL] File Tree:\n{result['tree']}")
                else:
                    print(f"❌ [TOOL] Tree failed: {result.get('error')}")
            except Exception as e:
                print(f"❌ [TOOL] Tree failed: {e}")

        # Detect FETCH_FILE
        fetch_matches = re.findall(r'<FETCH_FILE prefix="([^"]+)"\s*/>', response)
        for prefix in fetch_matches:
            print(f"⚡ [TOOL] Fetching file with prefix '{prefix}'...")
            try:
                from agent.tools import FileTrieIndexerTool
                tool = FileTrieIndexerTool()
                result = tool.execute(prefix=prefix)
                if result["success"]:
                    print(f"✅ [TOOL] Found {result['count']} match(es):")
                    for m in result["matches"]:
                        print(f"  • {os.path.relpath(m, os.getcwd())}")
                else:
                    print(f"❌ [TOOL] Fetch failed (Check if index is built)")
            except Exception as e:
                print(f"❌ [TOOL] Fetch failed: {e}")

        # Detect SAVE_MEMORY
        memory_matches = re.findall(r'<SAVE_MEMORY key="([^"]+)" value="([^"]+)"\s*/>', response)
        for key, value in memory_matches:
            print(f"🧠 [TOOL] Learning: {key} = {value}")
            UserMemory.update(key, value)
    
    def start_web_server(self, quiet=False):
        """Start the web server for phone access."""
        NovaWebHandler.nova_instance = self.nova
        
        ips = SystemControl.get_ip_addresses()
        local_ip = ips['local'][0]['ip'] if ips['local'] else 'localhost'
        self.local_ip = local_ip
        
        try:
            server = HTTPServer(('0.0.0.0', WEB_PORT), NovaWebHandler)
            
            if not quiet:
                if RICH_AVAILABLE and console:
                    console.print(f"\n  [green][OK][/] Web server started!")
                    console.print(f"  [cyan]Local:[/] http://localhost:{WEB_PORT}")
                    console.print(f"  [cyan]Network:[/] http://{local_ip}:{WEB_PORT}")
                    console.print(f"  [dim]Access from your phone on the same network[/]\n")
                else:
                    print(f"\n  Web server: http://{local_ip}:{WEB_PORT}\n")
            
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.web_server = server
            return server
        except Exception as e:
            print(f"  Web server failed: {e}")
            return None
    
    def start_bluetooth_server(self):
        """Start the Bluetooth server for phone access."""
        if not BLUETOOTH_AVAILABLE:
            if RICH_AVAILABLE and console:
                console.print("\n  [red][X] Bluetooth module not available![/]")
                console.print("  [dim]Run: pip install pyserial[/]\n")
            else:
                print("\n  Bluetooth module not available!")
                print("  Run: pip install pyserial\n")
            return None
        
        if self.bluetooth_server and self.bluetooth_server.running:
            if RICH_AVAILABLE and console:
                console.print("\n  [yellow]Bluetooth server already running![/]\n")
            else:
                print("\n  Bluetooth server already running!\n")
            return self.bluetooth_server
        
        if RICH_AVAILABLE and console:
            console.print("\n  [cyan]Starting Bluetooth Server...[/]")
            console.print("\n  [dim]Available COM ports:[/]")
        else:
            print("\n  Starting Bluetooth Server...")
            print("\n  Available COM ports:")
        
        # List available ports
        list_com_ports()
        
        # Get port from user
        try:
            if RICH_AVAILABLE:
                port = Prompt.ask("[cyan]Enter COM port (e.g., COM5) or Enter for auto[/]", default="")
            else:
                port = input("Enter COM port (e.g., COM5) or Enter for auto: ").strip()
            
            self.bluetooth_server = BluetoothServer(nova_instance=self.nova)
            
            if port:
                success = self.bluetooth_server.start(port=port)
            else:
                success = self.bluetooth_server.start()
            
            if success:
                if RICH_AVAILABLE and console:
                    console.print("\n  [green][OK] Bluetooth server started![/]")
                    console.print("  [dim]Use 'Serial Bluetooth Terminal' app on your phone[/]\n")
            
            return self.bluetooth_server if success else None
            
        except Exception as e:
            print(f"  Bluetooth server failed: {e}")
            return None

    def start_ble_server(self, name="Nova-BLE"):
        """Start the BLE server specifically for iPhone compatibility."""
        if not BLE_MODE_AVAILABLE:
            if RICH_AVAILABLE and console:
                console.print("\n  [red][X] BLE (iPhone mode) not available![/]")
                console.print("  [dim]Run: pip install bless[/]\n")
            else:
                print("\n  BLE Mode not available! Run: pip install bless")
            return None

        if self.ble_server and self.ble_server.running:
            if RICH_AVAILABLE and console:
                console.print("\n  [yellow]BLE server already running![/]\n")
            else:
                print("\n  BLE server already running!\n")
            return self.ble_server

        try:
            self.ble_server = BleServer(nova_instance=self.nova)
            if self.ble_server.start(name=name):
                if RICH_AVAILABLE and console:
                    console.print(f"\n  [green][OK] BLE Server '{name}' started![/]")
                    console.print("  [dim]Compatible with iPhone / BluetoothKit[/]\n")
                return self.ble_server
            return None
        except Exception as e:
            print(f"  BLE server failed: {e}")
            return None
    
    def start_agent_mode(self):
        """Start the MCP Agent mode for code generation and execution."""
        if not AGENT_AVAILABLE:
            if RICH_AVAILABLE and console:
                console.print("\n  [red][X] MCP Agent not available![/]")
                console.print("  [dim]Check if agent/agent.py exists[/]\n")
            else:
                print("\n  MCP Agent not available!")
            return
        
        if RICH_AVAILABLE and console:
            console.print("\n  [cyan]Starting MCP Agent Mode...[/]")
            console.print("  [dim]Type your prompt to generate and execute Python code[/]")
            console.print("  [dim]Type 'exit' or '/back' to return to NOVA[/]\n")
        else:
            print("\n  Starting MCP Agent Mode...")
            print("  Type your prompt to generate and execute Python code")
            print("  Type 'exit' or '/back' to return to NOVA\n")
        
        # Get current model from NOVA
        model_info = self.nova.get_current_model_info()
        model_name = model_info.get("name", "nova")
        
        # Initialize agent (works with both EnhancedMCPAgent and original MCPAgent)
        try:
            agent = MCPAgent(model=model_name)
        except Exception as e:
            print(f"  Error initializing agent: {e}")
            return
        
        while True:
            try:
                if RICH_AVAILABLE and console:
                    console.print("[bold magenta]AGENT>[/] ", end="")
                else:
                    print("AGENT> ", end="")
                
                prompt = input().strip()
                
                if not prompt:
                    continue
                
                if prompt.lower() in ["exit", "/back", "/exit", "quit"]:
                    if RICH_AVAILABLE and console:
                        console.print("\n  [cyan]Returning to NOVA...[/]\n")
                    else:
                        print("\n  Returning to NOVA...\n")
                    break
                
                # Run the agent
                print()
                result = agent.run(prompt)
                
                if RICH_AVAILABLE and console:
                    console.print("\n" + "-" * 50)
                    
                    # Show file path if created
                    if result.get("data") and result["data"].get("filepath"):
                        filepath = result["data"]["filepath"]
                        console.print(f"[bold green]✅ Success:[/] Created and executed {os.path.basename(filepath)}")
                    elif result.get("filepath"):
                        console.print(f"[bold green]✅ Success:[/] Created {os.path.basename(result['filepath'])}")
                    
                    # Show code ONLY if present and not suppressed
                    if result.get("code"):
                        console.print("[bold cyan]📄 Generated Code:[/]")
                        code_lines = result["code"].split("\n")
                        for line in code_lines[:15]:
                            console.print(f"  [dim]{line}[/]")
                        if len(code_lines) > 15:
                            console.print(f"  [dim]... ({len(code_lines) - 15} more lines)[/]")
                    
                    # Show output/result
                    if result.get("output") and result["output"].strip():
                        # If output looks like LLM chatter and we found an action, maybe skip it?
                        # For now, just show it clearly
                        console.print("\n[bold cyan]▶ Result:[/]")
                        console.print(result["output"])
                    
                    # Show errors if any
                    if result.get("errors") and not result.get("success"):
                        console.print(f"\n[bold red]❌ Errors:[/]\n{result['errors']}")
                    
                    console.print("-" * 50 + "\n")
                else:
                    print("\n" + "-" * 50)
                    if result.get("output"):
                        print(f"▶ Result: {result['output']}")
                    print("-" * 50 + "\n")
                
            except KeyboardInterrupt:
                print("\n")
                break
            except Exception as e:
                print(f"  Agent error: {e}\n")
    
    def print_help(self):
        help_text = """
## NOVA Commands

### System Control
- "What's the system status?"
- "Open Chrome / Notepad / VS Code"
- "Close notepad.exe"
- "Lock / Sleep / Shutdown / Restart"
- "Show running apps"
- "Search for files named report"

### Power Commands  
- "Gigathon sleep" / "Gigathon shutdown" / "Gigathon restart"

### Coding
- "Create a Python script..."
- "Read main.py and explain it"
- "Run pytest"

### CLI Commands
| Command | Description |
|---------|-------------|
| `/help` | Show this help |
| `/check` | System diagnostics |
| `/model` | Change AI model |
| `/bt` | 📱 Phone Remote (BLE/iPhone mode) |
| `/web` | Start web server for phone access |
| `/agent` | MCP Agent (code generation) |
| `/voice` | Voice command mode |
| `/clear` | Clear screen |
| `/exit` | Exit NOVA |

### 📱 Phone Remote Features (via /bt)
- PIN-based unlock (default: 1234)
- Lock / Sleep / Wake / Mute
- Volume & Brightness control
- Open/Close apps (single/double tap)
- Clear temp files
- Full AI chat with Groq
"""
        if RICH_AVAILABLE and console:
            console.print(Markdown(help_text))
        else:
            print(help_text)
    
    def show_model_selector(self):
        """Interactive model selector."""
        if RICH_AVAILABLE and console:
            console.print("\n-----------------------------------------------------------------------")
            console.print("[bold white]                         SELECT AI MODEL[/]")
            console.print("-----------------------------------------------------------------------\n")
            
            table = Table(box=box.ASCII, border_style="cyan", show_header=True, header_style="bold white")
            table.add_column("#", style="bold yellow", width=3)
            table.add_column("Model", style="bright_white", width=25)
            table.add_column("Description", style="dim", width=40)
            table.add_column("", style="green", width=10)
            
            for num, info in MODELS.items():
                current = "<- current" if num == self.nova.current_model else ""
                name = info["name"].split("/")[-1][:25]
                table.add_row(num, name, info["description"], current)
            
            console.print(table)
            console.print()
            
            try:
                choice = Prompt.ask("[cyan]Enter number (or Enter to cancel)[/]", default="")
                if choice and choice in MODELS:
                    if self.nova.set_model(choice):
                        console.print(f"\n[green][OK] Switched to {MODELS[choice]['name'].split('/')[-1]}[/]\n")
                    else:
                        console.print(f"\n[red][X] Cannot use this model[/]\n")
            except:
                pass
        else:
            print("\nModels:")
            for num, info in MODELS.items():
                print(f"  {num}. {info['description']}")
            choice = input("Enter number: ").strip()
            if choice in MODELS:
                self.nova.set_model(choice)
    
    def _handle_neural_intent(self, user_input):
        """Intersects input with the Neural Intent Engine. Returns True if handled."""
        if not self.nie:
            return False
            
        res = self.nie.process_command(user_input)
        intent = res.get('intent_name', 'UNKNOWN')
        confidence = res.get('confidence', 0)
        

        # MANUAL INTERCEPTION for critical commands
        lower_input = user_input.lower()
        if 'restart' in lower_input or 'gigathon restart' in lower_input:
             res['intent_name'] = "RESTART_SYSTEM"
             res['intent_id'] = 6
             res['confidence'] = 1.0
             intent = "RESTART_SYSTEM"
             confidence = 1.0
        elif 'shutdown' in lower_input or 'turn off' in lower_input or 'gigathon shutdown' in lower_input:
             res['intent_name'] = "SHUTDOWN_SYSTEM"
             res['intent_id'] = 5
             res['confidence'] = 1.0
             intent = "SHUTDOWN_SYSTEM"
             confidence = 1.0
        elif 'sleep' in lower_input or 'gigathon sleep' in lower_input:
             res['intent_name'] = "SLEEP_SYSTEM"
             res['intent_id'] = 7
             res['confidence'] = 1.0
             intent = "SLEEP_SYSTEM"
             confidence = 1.0

        # We only take over if we are very confident and it's a known system intent
        if confidence >= 0.75 and intent != "UNKNOWN":
            # Strict mode for SYSTEM_STATUS: user must actually say 'status' or 'info' or 'health'
            # This prevents common words like "great" or "power" from triggering it
            if intent == "SYSTEM_STATUS":
                trigger_words = ['status', 'info', 'health', 'report', 'stats']
                if not any(word in user_input.lower() for word in trigger_words):
                    return False
                    
            if RICH_AVAILABLE and console:
                # Beautiful Neural Panel
                title = f"[bold bright_cyan]🧠 Neural Interception[/]"
                content = f"Detected Intent: [bold orange1]{intent}[/]\nConfidence: [bold green]{confidence*100:.2f}%[/]\n\nThis command is being handled by your local Neural Engine."
                console.print(Panel(content, title=title, border_style="bright_cyan", padding=(1, 2)))
                
                # Manual Permission Gate for Nova CLI
                if Prompt.ask(f"\n🛡️  [bold yellow]PERMISSION REQUEST[/]\nConfirm execution?", choices=["y", "n"], default="n") == "y":
                    PermissionGate.execute_intent(res['intent_id'])
                    console.print("\n[bold green]✅ Action Executed via Local Brain.[/]\n")
                    return True
                else:
                    console.print("\n[bold red]🚫 Operation Aborted.[/]\n")
                    return True 
            else:
                print(f"\n🧠 Thinking... {intent} ({confidence*100:.1f}%)")
                if PermissionGate.ask_permission(intent, confidence):
                    PermissionGate.execute_intent(res['intent_id'])
                    return True
                return True
        
        return False

    def run(self):
        """Main CLI loop."""
        global VOICE_REPLY_ENABLED
        # Clear screen and print banner
        os.system('cls' if platform.system() == 'Windows' else 'clear')
        self.print_banner()
        
        if not self.nova.initialize():
            sys.exit(1)
        
        model_info = self.nova.get_current_model_info()
        model_name = model_info["name"].split("/")[-1]
        
        if RICH_AVAILABLE and console:
            console.print(f"  [green][OK][/] Ready! Using {model_name}")
            if self.nie:
                console.print(f"  [cyan][BRAIN][/] Neural Intent Engine Active")
        else:
            print(f"  [OK] Ready! Using {model_name}")
            if self.nie:
                print(f"  [BRAIN] Neural Intent Engine Active")
        
        self.print_status()
        
        # Auto-start web server for phone access
        self.local_ip = "localhost"
        self.start_web_server(quiet=True)
        
        if RICH_AVAILABLE and console:
            console.print(f"\n  Type /help for commands")
            console.print(f"  Phone: http://{self.local_ip}:{WEB_PORT}\n")
        else:
            print(f"\n  Phone access: http://{self.local_ip}:{WEB_PORT}\n")
        
        while True:
            try:
                if RICH_AVAILABLE and console:
                    console.print("[bold cyan]NOVA>[/] ", end="")
                else:
                    print("NOVA> ", end="")
                
                user_input = input().strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.startswith("/"):
                    cmd = user_input.lower().split()[0]
                    
                    if cmd in ["/exit", "/quit", "/q"]:
                        if RICH_AVAILABLE and console:
                            console.print(f"\n  [cyan]Goodbye, sir. {DEVICE_NAME} will be waiting.[/]\n")
                        else:
                            print(f"\n  Goodbye, sir. {DEVICE_NAME} will be waiting.\n")
                        break
                    
                    elif cmd == "/help":
                        self.print_help()
                    
                    elif cmd == "/status":
                        self.print_status()
                    
                    elif cmd == "/model":
                        self.show_model_selector()
                    
                    elif cmd == "/web":
                        self.start_web_server()
                    
                    elif cmd == "/clear":
                        os.system('cls' if platform.system() == 'Windows' else 'clear')
                        self.print_banner()
                    
                    elif cmd == "/check":
                        print("\n🔍 [NOVA DIAGNOSTICS]")
                        g_stats = GroqChat.diagnostics()
                        print(f"  • Groq API Key: {'✅ Loaded' if g_stats['has_key'] else '❌ Missing'}")
                        if g_stats['has_key']:
                            print(f"    (Preview: {g_stats['key_preview']})")
                        print(f"  • Groq Library: {'✅ Installed' if g_stats['library_installed'] else '❌ Missing'}")
                        print(f"  • Groq Ready:   {'✅ YES' if g_stats['available'] else '❌ NO (Restart Nova needed)'}")
                        print(f"  • Agent Tools:  {'✅ Ready' if AGENT_AVAILABLE else '❌ Missing'}")
                        print(f"  • .env Path:    {g_stats['env_path']}")
                        print(f"  • NIE Active:   {'✅' if NIE_AVAILABLE else '❌'}")
                        print(f"  • Voice/TTS:    {'✅' if VOICE_AVAILABLE else '❌'}")
                        print(f"  • Voice Reply:  {'✅ ON' if VOICE_REPLY_ENABLED else '❌ OFF (Normal mode)'}\n")
                    
                    elif cmd == "/bluetooth" or cmd == "/bt":
                        # Multi-mode choice
                        if BLE_MODE_AVAILABLE:
                            print("\n  [cyan][BLUEOOTH MODE SELECTION][/]")
                            print("  1. Classic Bluetooth (Android / Windows)")
                            print("  2. BLE Mode (iPhone / Apple Friendly)")
                            
                            choice = input("\n  Select mode [1/2]: ").strip()
                            if choice == '2':
                                self.start_ble_server()
                            else:
                                self.start_bluetooth_server()
                        else:
                            self.start_bluetooth_server()

                    elif cmd == "/ble":
                        self.start_ble_server()
                    
                    elif cmd == "/agent":
                        self.start_agent_mode()
                    
                    elif cmd == "/voice":
                        if SR_AVAILABLE:
                            print("\n  🎤 Voice Mode Activated!")
                            print("  Speak your command... (say 'exit' or 'stop' to deactivate)\n")
                            if VOICE_AVAILABLE:
                                VoiceControl.speak("Hello! Voice mode is now active. How can I help you?", force=True)
                            
                            voice_mode_active = True
                            while voice_mode_active:
                                voice_input = VoiceControl.listen(timeout=10)
                                if voice_input:
                                    if 'exit' in voice_input or 'stop' in voice_input or 'quit' in voice_input or 'deactivate' in voice_input:
                                        print("  🔇 Voice mode deactivated.\n")
                                        if VOICE_AVAILABLE:
                                            VoiceControl.speak("Goodbye! Voice mode deactivated.", force=True)
                                        voice_mode_active = False
                                        break
                                    
                                    # Process the voice command right here
                                    print(f"\n  📝 Processing: {voice_input}")
                                    lower_voice = voice_input.lower().strip()
                                    
                                    # ===== CONVERSATIONAL RESPONSES (Human-like) =====
                                    if lower_voice in ['hello', 'hi', 'hey', 'hello nova', 'hi nova', 'hey nova']:
                                        response = "Hello! I'm Nova, your AI assistant. What can I do for you?"
                                        print(f"  🗣️ {response}")
                                        # No voice for simple greetings
                                    
                                    elif 'how are you' in lower_voice:
                                        response = "I'm doing great, thank you for asking! I'm ready to help you with anything."
                                        print(f"  🗣️ {response}")
                                        if VOICE_AVAILABLE:
                                            VoiceControl.speak(response, force=True)
                                    
                                    elif 'thank you' in lower_voice or 'thanks' in lower_voice:
                                        response = "You're welcome! Happy to help."
                                        print(f"  🗣️ {response}")
                                        if VOICE_AVAILABLE:
                                            VoiceControl.speak(response, force=True)
                                    
                                    elif 'what can you do' in lower_voice or 'help' in lower_voice:
                                        response = "I can open apps, search Google, play YouTube videos, tell you the time, and much more. Just ask!"
                                        print(f"  🗣️ {response}")
                                        if VOICE_AVAILABLE:
                                            VoiceControl.speak(response, force=True)
                                    
                                    # ===== ACTION COMMANDS =====
                                    elif lower_voice in ['time', 'what time is it', "what's the time"]:
                                        from datetime import datetime
                                        current_time = datetime.now().strftime('%I:%M %p')
                                        response = f"The current time is {current_time}"
                                        print(f"  🕐 {response}")
                                        if VOICE_AVAILABLE:
                                            VoiceControl.speak(response, force=True)
                                    
                                    elif 'open' in lower_voice or 'launch' in lower_voice:
                                        app = lower_voice.replace('open', '').replace('launch', '').strip()
                                        response = f"Opening {app} for you"
                                        print(f"  🚀 {response}...")
                                        os.system(f'start {app}')
                                        if VOICE_AVAILABLE:
                                            VoiceControl.speak(response, force=True)
                                    
                                    elif 'close' in lower_voice:
                                        app = lower_voice.replace('close', '').strip()
                                        response = f"Closing {app}"
                                        print(f"  ❌ {response}...")
                                        os.system(f'taskkill /f /im {app}.exe 2>nul')
                                        if VOICE_AVAILABLE:
                                            VoiceControl.speak(response, force=True)
                                    
                                    elif 'play' in lower_voice:
                                        query = lower_voice.replace('play', '').strip()
                                        response = f"Playing {query} on YouTube for you"
                                        print(f"  🎵 {response}...")
                                        search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                                        os.system(f'start "" "{search_url}"')
                                        if VOICE_AVAILABLE:
                                            VoiceControl.speak(response, force=True)
                                    
                                    elif 'google' in lower_voice or 'search' in lower_voice:
                                        query = lower_voice.replace('google', '').replace('search', '').strip()
                                        response = f"Searching for {query}"
                                        print(f"  🔍 {response}...")
                                        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                                        os.system(f'start "" "{search_url}"')
                                        if VOICE_AVAILABLE:
                                            VoiceControl.speak(response, force=True)
                                    
                                    # ===== INTELLIGENT QUESTION ANSWERING (Siri-like) =====
                                    elif any(q in lower_voice for q in ['what is', 'who is', 'tell me about', 'explain', 'define', 'what are', 'how does', 'why is']):
                                        print("  🧠 Searching for intelligent answer...")
                                        if VOICE_AVAILABLE:
                                            VoiceControl.speak("Let me find that for you.", force=True)
                                        WebIntelligence.answer_with_voice(voice_input, force=True)
                                    
                                    elif lower_voice.endswith('?'):
                                        # Any question - use WebIntelligence
                                        print("  🧠 Finding answer to your question...")
                                        WebIntelligence.answer_with_voice(voice_input, force=True)
                                    
                                    else:
                                        # Generic conversational response
                                        response = f"I heard you say: {voice_input}. How can I help with that?"
                                        print(f"  💬 {response}")
                                        if VOICE_AVAILABLE:
                                            VoiceControl.speak(response, force=True)
                                    
                                    print("\n  🎤 Listening for next command...\n")
                        else:
                            print("  ⚠️ Voice recognition not available.")
                            print("  Install: pip install speechrecognition pyaudio\n")
                    
                    elif cmd == "/speak" or cmd == "/tts":
                        if VOICE_AVAILABLE:
                            VOICE_REPLY_ENABLED = not VOICE_REPLY_ENABLED
                            status = "ON" if VOICE_REPLY_ENABLED else "OFF"
                            print(f"  🔊 Text-to-Speech replies are now {status}")
                            if VOICE_REPLY_ENABLED:
                                VoiceControl.speak("Voice replies are now enabled.", force=True)
                        else:
                            print("  ⚠️ Text-to-Speech not available.")
                            print("  Install: pip install pyttsx3\n")
                    
                    elif cmd == "/help":
                        print("\n  📚 Nova Commands:")
                        print("  /exit     - Exit Nova")
                        print("  /clear    - Clear screen")
                        print("  /voice    - Enable voice input mode")
                        print("  /speak    - Test text-to-speech")
                        print("  /web      - Start web server")
                        print("  /agent    - Start agent mode")
                        print("  /help     - Show this help\n")
                    
                    else:
                        print(f"  Unknown command: {cmd}")
                    
                    print()
                    continue
                # 0. Quick System Commands (Bypass LLM for speed)
                lower_input = user_input.lower().strip()
                quick_handled = False
                
                # Exit commands - must be checked first!
                if lower_input in ['exit', 'quit', 'bye', 'goodbye']:
                    if RICH_AVAILABLE and console:
                        console.print(f"\n  [cyan]Goodbye, sir. {DEVICE_NAME} will be waiting.[/]\n")
                    else:
                        print(f"\n  Goodbye, sir. {DEVICE_NAME} will be waiting.\n")
                    break

                # 0. Neural Interception (Local Brain) - Handle critical system intents first
                if self._handle_neural_intent(user_input):
                    continue
                
                # ============= CHATBOT RESPONSES (Priority - handle conversational queries first) =============
                # Check if NovaChatBot can handle this as a conversational query
                # Short patterns need exact/word-boundary match, long patterns use substring
                exact_match_patterns = ['hi', 'hey', 'bye', 'joke', 'thanks', 'thank you']
                phrase_patterns = ['who are you', 'your name', 'how are you', 'what can you do', 
                                   'tell me a joke', 'hello', 'goodbye', 'motivate', 'inspire', 
                                   'who made you', 'who created you', 'how old are you', 
                                   'do you love me', 'meaning of life', 'help me',
                                   'good morning', 'good afternoon', 'good evening', 'good night',
                                   'you are great', 'you are awesome', 'i love you', 'i am sad', 'cheer me up']
                
                # Check exact matches first (whole input = pattern)
                is_exact_match = lower_input.strip() in exact_match_patterns
                # Check phrase patterns (substring match for longer phrases)
                is_phrase_match = any(p in lower_input for p in phrase_patterns)
                
                is_conversational = is_exact_match or is_phrase_match
                
                if is_conversational:
                    # Let chatbot handle it
                    response = NovaChatBot.get_response(user_input)
                    print(f"\n🤖 Nova: {response}\n")
                    # Skip voice for simple greetings
                    simple_greetings = ['hello', 'hi', 'hey', 'bye', 'goodbye']
                    if VOICE_AVAILABLE and lower_input.strip() not in simple_greetings:
                        VoiceControl.speak(response[:200])
                    continue
                
                # ============= QUESTION DETECTION (for factual questions - use Groq/WebIntelligence) =============
                # Detect questions and use Groq AI (if available) or WebIntelligence
                question_starters = ['what is', 'who is', 'what are', 'who are', 'how is', 'how does', 
                                    'why is', 'why are', 'when is', 'when was', 'where is', 'where was',
                                    'explain', 'define', 'tell me about', 'what does', 'how to', 'can you', 
                                    'write', 'create', 'generate', 'show me', 'help with']
                is_question = any(lower_input.startswith(q) for q in question_starters) or (lower_input.endswith('?') and len(lower_input) > 3)
                
                # If it's a question or a long sentence, prioritize Groq AI
                is_complex = len(lower_input.split()) > 4 or is_question
                
                if is_complex and GROQ_AVAILABLE:
                    print()
                    if RICH_AVAILABLE and console:
                        with console.status("[bold bright_cyan]  🤖 Thinking...", spinner="dots"):
                            response = GroqChat.chat(user_input)
                    else:
                        print("  🤖 Thinking...")
                        response = GroqChat.chat(user_input)
                    
                    print()
                    if RICH_AVAILABLE and console:
                        console.print(Panel(response, title="[bold bright_cyan]🤖 NOVA[/]", 
                                            border_style="bright_cyan", padding=(1, 2)))
                    else:
                        print(f"🤖 NOVA: {response}")
                    
                    if VOICE_AVAILABLE:
                        spoken = response[:250] + "..." if len(response) > 250 else response
                        VoiceControl.speak(spoken)
                    
                    # Process any tool calls (new!)
                    self._process_tool_calls(response)
                    continue

                if is_question and not GROQ_AVAILABLE:
                    print("🧠 Searching for intelligent answer...")
                    if VOICE_AVAILABLE:
                        VoiceControl.speak("Let me find that for you.")
                    WebIntelligence.answer_with_voice(user_input)
                    continue  # Skip to next input
                
                # ============= CLOSE APP COMMANDS (must be before NLP matching) =============
                if lower_input.startswith('close '):
                    app_to_close = lower_input.replace('close ', '').strip()
                    process_map = {
                        'chrome': 'chrome.exe',
                        'edge': 'msedge.exe',
                        'firefox': 'firefox.exe',
                        'notepad': 'notepad.exe',
                        'calculator': 'CalculatorApp.exe',
                        'calc': 'CalculatorApp.exe',
                        'word': 'WINWORD.EXE',
                        'excel': 'EXCEL.EXE',
                        'powerpoint': 'POWERPNT.EXE',
                        'spotify': 'Spotify.exe',
                        'discord': 'Discord.exe',
                        'vscode': 'Code.exe',
                        'vs code': 'Code.exe',
                        'code': 'Code.exe',
                        'explorer': 'explorer.exe',
                        'teams': 'Teams.exe',
                        'slack': 'slack.exe',
                        'terminal': 'WindowsTerminal.exe',
                        'cmd': 'cmd.exe',
                        'powershell': 'powershell.exe',
                        'phone link': 'PhoneExperienceHost.exe',
                        'phonelink': 'PhoneExperienceHost.exe',
                        'your phone': 'YourPhone.exe',
                        'instagram': 'instagram.exe',
                        'whatsapp': 'WhatsApp.exe',
                        'telegram': 'Telegram.exe',
                        'zoom': 'Zoom.exe',
                        'skype': 'Skype.exe',
                        'vlc': 'vlc.exe',
                        'obs': 'obs64.exe',
                        'steam': 'steam.exe',
                        'task manager': 'Taskmgr.exe',
                        'taskmgr': 'Taskmgr.exe',
                        'snipping tool': 'SnippingTool.exe',
                        'paint': 'mspaint.exe',
                        'xbox': 'XboxApp.exe',
                        'roblox': 'RobloxPlayerBeta.exe',
                    }
                    
                    process_name = process_map.get(app_to_close.lower())
                    if process_name:
                        if RICH_AVAILABLE and console:
                            console.print(f"\n[bold bright_cyan]❌ Closing {app_to_close.title()}...[/]")
                        else:
                            print(f"❌ Closing {app_to_close.title()}...")
                        os.system(f'taskkill /f /im {process_name} 2>nul')
                        print(f"✅ {app_to_close.title()} closed")
                    else:
                        # Try to close by process name directly
                        print(f"❌ Closing {app_to_close}...")
                        os.system(f'taskkill /f /im {app_to_close}.exe 2>nul')
                        # Also try with spaces replaced by no space
                        os.system(f'taskkill /f /im {app_to_close.replace(" ", "")}.exe 2>nul')
                        print(f"✅ Attempted to close {app_to_close}")
                    quick_handled = True
                    continue  # Skip to next input
                
                # Understands natural language like "open vs code", "play youtube", etc.
                
                # Define keyword mappings: keywords -> (action, display_name)
                APP_KEYWORDS = {
                    # Desktop Apps
                    ('chrome', 'google chrome'): ('start chrome', 'Chrome'),
                    ('firefox',): ('start firefox', 'Firefox'),
                    ('edge', 'microsoft edge'): ('start msedge', 'Edge'),
                    ('notepad', 'text editor'): ('start notepad', 'Notepad'),
                    ('vscode', 'vs code', 'visual studio code', 'code editor'): ('start code', 'VS Code'),
                    ('calculator', 'calc'): ('start calc', 'Calculator'),
                    ('explorer', 'file explorer', 'files', 'folders'): ('start explorer', 'File Explorer'),
                    ('terminal', 'cmd', 'command prompt'): ('start cmd', 'Terminal'),
                    ('powershell',): ('start powershell', 'PowerShell'),
                    ('settings', 'windows settings'): ('start ms-settings:', 'Settings'),
                    ('spotify', 'music'): ('start spotify:', 'Spotify'),
                    ('discord',): ('start discord:', 'Discord'),
                    ('word', 'microsoft word'): ('start winword', 'Word'),
                    ('excel', 'microsoft excel'): ('start excel', 'Excel'),
                    ('paint',): ('start mspaint', 'Paint'),
                    ('phone link', 'phonelink', 'your phone'): ('start ms-phone:', 'Phone Link'),
                    ('xbox',): ('start xbox:', 'Xbox'),
                    ('store', 'microsoft store'): ('start ms-windows-store:', 'Microsoft Store'),
                    ('snipping tool', 'snip'): ('start snippingtool', 'Snipping Tool'),
                    ('task manager',): ('start taskmgr', 'Task Manager'),
                    ('control panel',): ('start control', 'Control Panel'),
                    
                    # Social Media
                    ('youtube', 'yt'): ('start https://youtube.com', 'YouTube'),
                    ('twitter', 'x.com'): ('start https://twitter.com', 'Twitter'),
                    ('instagram', 'insta'): ('start https://instagram.com', 'Instagram'),
                    ('facebook', 'fb'): ('start https://facebook.com', 'Facebook'),
                    ('linkedin',): ('start https://linkedin.com', 'LinkedIn'),
                    ('whatsapp',): ('start https://web.whatsapp.com', 'WhatsApp'),
                    ('reddit',): ('start https://reddit.com', 'Reddit'),
                    ('tiktok',): ('start https://tiktok.com', 'TikTok'),
                    ('twitch',): ('start https://twitch.tv', 'Twitch'),
                    
                    # AI Tools
                    ('chatgpt', 'chat gpt', 'openai'): ('start https://chat.openai.com', 'ChatGPT'),
                    ('claude', 'anthropic'): ('start https://claude.ai', 'Claude'),
                    ('gemini', 'bard', 'google ai'): ('start https://gemini.google.com', 'Gemini'),
                    ('perplexity',): ('start https://perplexity.ai', 'Perplexity'),
                    ('copilot', 'bing ai'): ('start https://copilot.microsoft.com', 'Copilot'),
                    ('huggingface', 'hugging face'): ('start https://huggingface.co', 'HuggingFace'),
                    ('midjourney',): ('start https://midjourney.com', 'Midjourney'),
                    
                    # Productivity
                    ('github',): ('start https://github.com', 'GitHub'),
                    ('gmail', 'email', 'mail'): ('start https://mail.google.com', 'Gmail'),
                    ('google drive', 'drive'): ('start https://drive.google.com', 'Google Drive'),
                    ('notion',): ('start https://notion.so', 'Notion'),
                    ('google', 'search'): ('start https://google.com', 'Google'),
                    ('stackoverflow', 'stack overflow'): ('start https://stackoverflow.com', 'Stack Overflow'),
                }
                
                # Check if input contains trigger words AND app keywords
                # Skip if it's a "close" command - those are handled separately
                trigger_words = ['open', 'launch', 'start', 'run', 'play', 'go to', 'show', 'bring up']
                is_close_command = lower_input.startswith('close ')
                has_trigger = any(trigger in lower_input for trigger in trigger_words) or lower_input.split()[0] if lower_input else False
                
                if not is_close_command and (has_trigger or len(lower_input.split()) <= 3):  # Short commands likely want to open something
                    import re
                    for keywords, (command, name) in APP_KEYWORDS.items():
                        matched = False
                        for kw in keywords:
                            # Use word boundary to avoid matching 'yt' in 'python'
                            # Stricter: must be a whole word match
                            if re.search(rf'\b{re.escape(kw)}\b', lower_input):
                                matched = True
                                break
                        
                        if matched:
                            # Verify it's not actually a complex sentence we should have handled earlier
                            if len(lower_input.split()) > 5:
                                # This is probably not a simple app launch
                                continue
                                
                            if RICH_AVAILABLE and console:
                                console.print(f"\n[bold bright_cyan]🚀 Opening {name}...[/]")
                            else:
                                print(f"🚀 Opening {name}...")
                            os.system(command)
                            if RICH_AVAILABLE and console:
                                console.print(f"[green]✅ {name} opened[/]\n")
                            else:
                                print(f"✅ {name} opened")
                            quick_handled = True
                            break
                
                # ============= SYSTEM CONTROL COMMANDS =============
                if not quick_handled:
                    if lower_input in ['mute', 'unmute', 'silence', 'quiet']:
                        if RICH_AVAILABLE and console:
                            console.print("\n[bold bright_cyan]🔇 Muting system volume...[/]")
                        result = SystemControl.set_volume(0)
                        if RICH_AVAILABLE and console:
                            console.print(f"[green]✅ {result}[/]\n")
                        else:
                            print(f"✅ {result}")
                        quick_handled = True
                    
                    elif lower_input in ['volume up', 'louder', 'increase volume']:
                        if RICH_AVAILABLE and console:
                            console.print("\n[bold bright_cyan]🔊 Increasing volume...[/]")
                        SystemControl.set_volume(75)
                        if RICH_AVAILABLE and console:
                            console.print("[green]✅ Volume set to 75%[/]\n")
                        else:
                            print("✅ Volume increased")
                        quick_handled = True
                    
                    elif lower_input in ['volume down', 'quieter', 'decrease volume']:
                        if RICH_AVAILABLE and console:
                            console.print("\n[bold bright_cyan]🔉 Decreasing volume...[/]")
                        SystemControl.set_volume(25)
                        if RICH_AVAILABLE and console:
                            console.print("[green]✅ Volume set to 25%[/]\n")
                        else:
                            print("✅ Volume decreased")
                        quick_handled = True
                    
                    elif lower_input in ['lock', 'lock screen', 'lock computer', 'lock pc']:
                        if RICH_AVAILABLE and console:
                            console.print("\n[bold bright_cyan]🔒 Locking screen...[/]")
                        SystemControl.lock_screen()
                        quick_handled = True
                    
                    # Brightness control
                    elif 'brightness' in lower_input:
                        if 'up' in lower_input or 'increase' in lower_input or '+' in lower_input:
                            if RICH_AVAILABLE and console:
                                console.print("\n[bold bright_cyan]☀️ Increasing brightness...[/]")
                            else:
                                print("☀️ Increasing brightness...")
                            # Use PowerShell to increase brightness
                            os.system('powershell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,80)"')
                            print("✅ Brightness increased to 80%")
                            quick_handled = True
                        elif 'down' in lower_input or 'decrease' in lower_input or '-' in lower_input:
                            if RICH_AVAILABLE and console:
                                console.print("\n[bold bright_cyan]🌙 Decreasing brightness...[/]")
                            else:
                                print("🌙 Decreasing brightness...")
                            os.system('powershell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,30)"')
                            print("✅ Brightness decreased to 30%")
                            quick_handled = True
                        elif 'max' in lower_input or '100' in lower_input:
                            os.system('powershell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,100)"')
                            print("✅ Brightness set to 100%")
                            quick_handled = True
                        elif 'min' in lower_input or '0' in lower_input:
                            os.system('powershell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,10)"')
                            print("✅ Brightness set to 10%")
                            quick_handled = True
                    
                    # ============= ASK COMMAND (Siri-like intelligent answers) =============
                    elif lower_input.startswith('ask '):
                        question = lower_input.replace('ask ', '').strip()
                        if question:
                            print("🧠 Searching for intelligent answer...")
                            if VOICE_AVAILABLE:
                                VoiceControl.speak("Let me find that for you.")
                            WebIntelligence.answer_with_voice(question)
                            quick_handled = True
                    
                    # ============= QUESTION DETECTION (Siri-like) =============
                    elif any(lower_input.startswith(q) for q in ['what is ', 'who is ', 'what are ', 'how does ', 'why is ', 'explain ', 'define ', 'tell me about ']):
                        print("🧠 Searching for intelligent answer...")
                        WebIntelligence.answer_with_voice(user_input)
                        quick_handled = True
                    
                    elif lower_input.endswith('?') and len(lower_input) > 10:
                        # Any question ending with ? 
                        print("🧠 Finding answer to your question...")
                        WebIntelligence.answer_with_voice(user_input)
                        quick_handled = True
                    
                    # ============= CLOSE APP COMMANDS (from Jarvis) =============
                    elif lower_input.startswith('close '):
                        app_to_close = lower_input.replace('close ', '').strip()
                        process_map = {
                            'chrome': 'chrome.exe',
                            'edge': 'msedge.exe',
                            'firefox': 'firefox.exe',
                            'notepad': 'notepad.exe',
                            'calculator': 'CalculatorApp.exe',
                            'calc': 'CalculatorApp.exe',
                            'word': 'WINWORD.EXE',
                            'excel': 'EXCEL.EXE',
                            'powerpoint': 'POWERPNT.EXE',
                            'spotify': 'Spotify.exe',
                            'discord': 'Discord.exe',
                            'vscode': 'Code.exe',
                            'vs code': 'Code.exe',
                            'code': 'Code.exe',
                            'explorer': 'explorer.exe',
                            'teams': 'Teams.exe',
                            'slack': 'slack.exe',
                        }
                        
                        process_name = process_map.get(app_to_close.lower())
                        if process_name:
                            if RICH_AVAILABLE and console:
                                console.print(f"\n[bold bright_cyan]❌ Closing {app_to_close.title()}...[/]")
                            else:
                                print(f"❌ Closing {app_to_close.title()}...")
                            os.system(f'taskkill /f /im {process_name} 2>nul')
                            print(f"✅ {app_to_close.title()} closed")
                        else:
                            # Try to close by process name directly
                            os.system(f'taskkill /f /im {app_to_close}.exe 2>nul')
                            print(f"✅ Attempted to close {app_to_close}")
                        quick_handled = True
                    
                    # ============= TIME/DATE COMMANDS (from Jarvis) =============
                    elif lower_input in ['time', 'what time is it', 'current time', 'what is the time']:
                        from datetime import datetime
                        current_time = datetime.now().strftime('%I:%M %p')
                        if RICH_AVAILABLE and console:
                            console.print(f"\n[bold bright_cyan]🕐 Current time: [yellow]{current_time}[/][/]\n")
                        else:
                            print(f"🕐 Current time: {current_time}")
                        quick_handled = True
                    
                    elif lower_input in ['date', 'what date is it', 'current date', 'what is the date', "what's the date"]:
                        from datetime import datetime
                        current_date = datetime.now().strftime('%A, %B %d, %Y')
                        if RICH_AVAILABLE and console:
                            console.print(f"\n[bold bright_cyan]📅 Today is: [yellow]{current_date}[/][/]\n")
                        else:
                            print(f"📅 Today is: {current_date}")
                        quick_handled = True
                    
                    # ============= YOUTUBE PLAYBACK (from Jarvis) =============
                    elif lower_input.startswith('play '):
                        query = lower_input.replace('play ', '').strip()
                        if query:
                            if RICH_AVAILABLE and console:
                                console.print(f"\n[bold bright_cyan]🎵 Playing '{query}' on YouTube...[/]")
                            else:
                                print(f"🎵 Playing '{query}' on YouTube...")
                            # Try pywhatkit first, fall back to browser
                            try:
                                import pywhatkit
                                pywhatkit.playonyt(query)
                            except ImportError:
                                # Fallback: open YouTube search
                                search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                                os.system(f'start "" "{search_url}"')
                            print(f"✅ Now playing: {query}")
                            quick_handled = True
                    
                    # ============= GOOGLE SEARCH (from jarvis-ai-assistant) =============
                    elif lower_input.startswith('google search ') or lower_input.startswith('search google '):
                        query = lower_input.replace('google search ', '').replace('search google ', '').strip()
                        if query:
                            if RICH_AVAILABLE and console:
                                console.print(f"\n[bold bright_cyan]🔍 Searching Google for '{query}'...[/]")
                            else:
                                print(f"🔍 Searching Google for '{query}'...")
                            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                            os.system(f'start "" "{search_url}"')
                            print(f"✅ Google search opened")
                            quick_handled = True
                    
                    # ============= YOUTUBE SEARCH (from jarvis-ai-assistant) =============
                    elif lower_input.startswith('youtube search ') or lower_input.startswith('search youtube '):
                        query = lower_input.replace('youtube search ', '').replace('search youtube ', '').strip()
                        if query:
                            if RICH_AVAILABLE and console:
                                console.print(f"\n[bold bright_cyan]📺 Searching YouTube for '{query}'...[/]")
                            else:
                                print(f"📺 Searching YouTube for '{query}'...")
                            search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
                            os.system(f'start "" "{search_url}"')
                            print(f"✅ YouTube search opened")
                            quick_handled = True
                    
                    # ============= WIKIPEDIA SEARCH =============
                    elif lower_input.startswith('wikipedia ') or lower_input.startswith('wiki '):
                        query = lower_input.replace('wikipedia ', '').replace('wiki ', '').strip()
                        if query:
                            if RICH_AVAILABLE and console:
                                console.print(f"\n[bold bright_cyan]📚 Searching Wikipedia for '{query}'...[/]")
                            else:
                                print(f"📚 Searching Wikipedia for '{query}'...")
                            search_url = f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}"
                            os.system(f'start "" "{search_url}"')
                            print(f"✅ Wikipedia opened")
                            quick_handled = True

                    elif lower_input in ['scan apps', 'rescan apps', 'find apps', 'refresh apps']:
                        if RICH_AVAILABLE and console:
                            console.print("\n[bold bright_cyan]🔍 Scanning for installed apps...[/]")
                        else:
                            print("🔍 Scanning for installed apps...")
                        if APP_FINDER:
                            count = APP_FINDER.rescan()
                            if RICH_AVAILABLE and console:
                                console.print(f"[green]✅ Found {count} apps![/]\n")
                            else:
                                print(f"✅ Found {count} apps!")
                        quick_handled = True
                    
                    # List Apps command
                    elif lower_input in ['list apps', 'show apps', 'my apps']:
                        if APP_FINDER:
                            count = APP_FINDER.get_app_count()
                            print(f"\n📱 {count} apps cached. Type 'scan apps' to refresh.\n")
                            # Show first 20 apps
                            apps_list = list(APP_FINDER.apps.keys())[:20]
                            for app in apps_list:
                                print(f"  • {app.title()}")
                            if count > 20:
                                print(f"  ... and {count - 20} more")
                            print()
                        quick_handled = True
                
                # ============= SMART APP FINDER (Fallback for any app) =============
                if not quick_handled and APP_FINDER:
                    # Check if input looks like an app launch request
                    trigger_words = ['open', 'launch', 'start', 'run']
                    has_trigger = any(lower_input.startswith(trigger + ' ') for trigger in trigger_words)
                    app_query = lower_input
                    
                    # Remove trigger words to get just the app name
                    for trigger in trigger_words:
                        if app_query.startswith(trigger + ' '):
                            app_query = app_query[len(trigger) + 1:].strip()
                            break
                    
                    # Only try to launch if:
                    # 1. Has explicit trigger word (open X, launch Y)
                    # 2. OR single word with 2-20 chars (likely app name)
                    is_likely_app_name = len(app_query.split()) == 1 and 2 <= len(app_query) <= 20
                    
                    if has_trigger or is_likely_app_name:
                        # Check if app exists in cache before trying to launch
                        app_name, app_path = APP_FINDER.find_app(app_query)
                        if app_path:
                            success, message = APP_FINDER.launch_app(app_query)
                            if success:
                                if RICH_AVAILABLE and console:
                                    console.print(f"\n[bold bright_cyan]🚀 {message}[/]\n")
                                else:
                                    print(f"🚀 {message}")
                                quick_handled = True

                if quick_handled:
                    continue
                
                # 1. Local Chatbot (For short expressions & greetings)
                # Catching these BEFORE neural interception prevents "great" from being "SYSTEM_STATUS"
                if len(user_input.split()) <= 3:
                    local_response = NovaChatBot.get_response(user_input)
                    if local_response and "I'm not sure I understand" not in local_response:
                        print()
                        if RICH_AVAILABLE and console:
                            console.print(Panel(local_response, title="[bold bright_cyan]🤖 NOVA[/]", 
                                                border_style="bright_cyan", padding=(1, 2)))
                        else:
                            print(f"🤖 NOVA: {local_response}")
                        
                        # Handle voice if enabled
                        if VOICE_AVAILABLE and VOICE_REPLY_ENABLED:
                             VoiceControl.speak(local_response)
                             
                        print()
                        continue

                # 2. Process with fallback (if nothing else caught it)
                print()
                if RICH_AVAILABLE and console:
                    with console.status("[bold bright_cyan]  🤖 Thinking...", spinner="dots"):
                        response = GroqChat.chat(user_input)
                else:
                    print("  🤖 Thinking...")
                    response = GroqChat.chat(user_input)
                
                print()
                if RICH_AVAILABLE and console:
                    console.print(Panel(response, title="[bold bright_cyan]🤖 NOVA[/]", 
                                        border_style="bright_cyan", padding=(1, 2)))
                else:
                    print(f"🤖 NOVA: {response}")
                
                # ============= TOOL CALL PARSER (Detect and execute file actions) =============
                self._process_tool_calls(response)
                
                # Speak the response
                if VOICE_AVAILABLE and VOICE_REPLY_ENABLED and response and "Error:" not in response:
                    spoken = response[:250] + "..." if len(response) > 250 else response
                    # Clean markdown for speech
                    spoken = spoken.replace('**', '').replace('*', '').replace('`', '')
                    spoken = spoken.replace('#', '').replace('\n', ' ')
                    VoiceControl.speak(spoken)
                
                print()
                
            except KeyboardInterrupt:
                print("\n")
                if RICH_AVAILABLE and console:
                    console.print("  [yellow]Ctrl+C again or /exit to quit[/]")
                else:
                    print("  Ctrl+C again or /exit to quit")
            except Exception as e:
                print(f"  Error: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="NOVA - AI Coding Assistant")
    parser.add_argument("--api-key", "-k", help="Gemini API key")
    parser.add_argument("--hf-token", help="HuggingFace token")
    parser.add_argument("--model", "-m", choices=list(MODELS.keys()), help="Model number (1-6)")
    parser.add_argument("--web", "-w", action="store_true", help="Start with web server")
    parser.add_argument("--version", "-v", action="version", version=f"NOVA v{NOVA_VERSION}")
    parser.add_argument("prompt", nargs="*", help="Run single prompt and exit")
    
    args = parser.parse_args()
    
    if args.api_key:
        os.environ["GEMINI_API_KEY"] = args.api_key
    if args.hf_token:
        os.environ["HF_TOKEN"] = args.hf_token
    
    cli = NovaCLI()
    
    if args.model:
        cli.nova.current_model = args.model
    
    if args.prompt:
        if cli.nova.initialize():
            response = cli.nova.process(" ".join(args.prompt))
            print(response)
        sys.exit(0)
    
    # Start web server if requested
    if args.web:
        if cli.nova.initialize():
            cli.start_web_server()
    
    cli.run()

if __name__ == "__main__":
    main()
