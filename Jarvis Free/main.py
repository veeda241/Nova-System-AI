import sys
import os
import time
import threading
import subprocess
import webbrowser
import json
import psutil 
import pyautogui 
import pyttsx3
import pyaudio 
import speech_recognition as sr
import pygame 
import whisper 
import ollama
from queue import Queue
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
from PyQt6.QtWebEngineWidgets import QWebEngineView 

hud_input_queue = Queue()

class StatusBridge(QObject):
    status_update = pyqtSignal(str, str)

ui_bridge = StatusBridge()

MODEL_NAME = "llama3"
VISION_MODEL = "llava"
MEMORY_FILE = "jervis_memory.json"

print("Loading local vision & brain...")
stt_model = whisper.load_model("base")

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, 'r') as f:
            return json.load(f)
    return [{"role": "system", "content": "You are Jervis, an advanced local AI by Rishav Biswas. You have access to the user's files and camera. address him as Boss."}]

messages = load_memory()

def save_memory():
    with open(MEMORY_FILE, 'w') as f:
        json.dump(messages[-20:], f)

is_jervis_speaking = False 
pygame.mixer.init()

def speak(text):
    global is_jervis_speaking
    ui_bridge.status_update.emit("SPEAKING", "Speaking...")
    try:
        local_engine = pyttsx3.init()
        local_engine.setProperty('rate', 200)
        local_engine.say(text)
        local_engine.runAndWait()
        local_engine.stop()
    except: pass
    is_jervis_speaking = False  
    ui_bridge.status_update.emit("IDLE", "System Online")

def analyze_vision(prompt, image_path):
    try:
        res = ollama.chat(model=VISION_MODEL, messages=[{'role': 'user', 'content': prompt, 'images': [image_path]}])
        return res['message']['content']
    except:
        return "Vision sensors are offline, Boss."

def run_system_task(command):
    cmd = command.lower()
    if "describe this" in cmd or "what is this" in cmd:
        pyautogui.screenshot("vision_temp.png")
        return analyze_vision("Describe what is on my screen right now.", "vision_temp.png")
    
    apps = {"youtube": "https://www.youtube.com", "github": "https://github.com", "gmail": "https://mail.google.com"}
    for app, url in apps.items():
        if app in cmd:
            webbrowser.open(url)
            return f"Opening {app}, Boss."

    if "play music" in cmd:
        music_dir = os.path.expanduser("~/Music")
        songs = [f for f in os.listdir(music_dir) if f.endswith('.mp3')]
        if songs:
            os.startfile(os.path.join(music_dir, songs[0]))
            return "Spinning the tracks now, Boss."
            
    try:
        if "screenshot" in cmd:
            pyautogui.screenshot("jervis_capture.png")
            os.startfile("jervis_capture.png")
            return "Screen captured and saved, Boss."
        elif "cpu" in cmd or "status" in cmd:
            usage = psutil.cpu_percent()
            return f"CPU is at {usage} percent. Everything is running smooth."
    except: pass
    return None

def jervis_brain():
    global is_jervis_speaking  
    recognizer = sr.Recognizer()
    threading.Thread(target=speak, args=("Jervis Advanced Local Cores Online. Ready for you, Boss.",), daemon=True).start()
    
    while True:
        try:
            while is_jervis_speaking: time.sleep(0.1)
            ui_bridge.status_update.emit("LISTENING", "Listening...")
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, phrase_time_limit=10)
            
            with open("temp.wav", "wb") as f: f.write(audio.get_wav_data())
            result = stt_model.transcribe("temp.wav")
            user_input = result["text"].strip()
            if len(user_input) < 2: continue

            task_response = run_system_task(user_input)
            if task_response:
                speak(task_response)
                continue

            messages.append({"role": "user", "content": user_input})
            response = ollama.chat(model=MODEL_NAME, messages=messages)
            resp_text = response['message']['content']
            
            messages.append({"role": "assistant", "content": resp_text})
            save_memory()
            
            is_jervis_speaking = True
            threading.Thread(target=speak, args=(resp_text,), daemon=True).start()
        except: continue

if __name__ == "__main__":
    app = QApplication(sys.argv)
    threading.Thread(target=jervis_brain, daemon=True).start()
    from hud_window import JervisHUD 
    hud = JervisHUD()
    sys.exit(app.exec())