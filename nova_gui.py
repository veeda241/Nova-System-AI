#!/usr/bin/env python3
import sys
import os
import time
import threading
import json
import psutil
import subprocess
from datetime import datetime
from pathlib import Path

try:
    from PyQt6.QtCore import Qt, QUrl, QObject, pyqtSlot, pyqtSignal, QTimer, QThread
    from PyQt6.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu
    from PyQt6.QtGui import QIcon, QAction
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebChannel import QWebChannel
    GUI_AVAILABLE = True
except ImportError:
    GUI_AVAILABLE = False
    # Dummy classes and functions to prevent NameError if imports fail
    class QObject: pass
    class QMainWindow: pass
    class QThread: pass
    class QTimer:
        def timeout(self): pass
        def start(self, ms): pass
    def pyqtSlot(*args, **kwargs):
        return lambda func: func
    def pyqtSignal(*args, **kwargs):
        class Signal:
            def emit(self, *a): pass
            def connect(self, f): pass
        return Signal()

# Import Nova Assistant
SCRIPT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from nova_layered import NovaLayeredAssistant
except ImportError:
    NovaLayeredAssistant = None

def powershell_tts(text):
    """Speak text using Windows PowerShell."""
    try:
        safe_text = text.replace('"', '').replace("'", "")
        cmd = f'powershell -Command "Add-Type –AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{safe_text}\');"'
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except:
        return False

class VoiceWorker(QObject):
    """Background voice listener."""
    command_detected = pyqtSignal(str)
    status_changed = pyqtSignal(str, str) # status, color

    def __init__(self, assistant=None):
        super().__init__()
        self.assistant = assistant
        self.running = True

    def run(self):
        try:
            import speech_recognition as sr
            recognizer = sr.Recognizer()
            recognizer.dynamic_energy_threshold = True
            recognizer.energy_threshold = 400
            
            while self.running:
                with sr.Microphone() as source:
                    self.status_changed.emit("AWAITING WAKE WORD", "#00d2ff")
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    try:
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                        text = recognizer.recognize_google(audio).lower()
                        print(f"Heard: {text}")
                        
                        if "nova" in text or "hey nova" in text:
                            powershell_tts("Yes Boss?")
                            self.status_changed.emit("LISTENING...", "#0f0")
                            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
                            cmd = recognizer.recognize_google(audio)
                            self.command_detected.emit(cmd)
                    except:
                        pass
                time.sleep(0.1)
        except Exception as e:
            print(f"Voice thread error: {e}")

class NovaInterface(QObject):
    """Bridge between Python and JavaScript."""
    def __init__(self, assistant, window):
        super().__init__()
        self.assistant = assistant
        self.window = window

    @pyqtSlot(str)
    def process_input(self, text):
        """Called from JavaScript when user sends a message."""
        print(f"HUD Input: {text}")
        if self.assistant:
            threading.Thread(target=self._run_assistant, args=(text,), daemon=True).start()

    @pyqtSlot()
    def capture_vision(self):
        """Called from JS to analyze screen."""
        try:
            import pyautogui
            screenshot_path = SCRIPT_DIR / "vision_temp.png"
            pyautogui.screenshot(str(screenshot_path))
            self.window.setStatus("ANALYZING SCREEN...", "#ffa500")
            threading.Thread(target=self._run_assistant, args=("Analyze my current screen content.",), daemon=True).start()
        except Exception as e:
            self.window.browser.page().runJavaScript(f"window.setNovaResponse('Vision error: {str(e)}')")

    @pyqtSlot()
    def exit_app(self):
        """Cleanly exit the application."""
        print("Exit signal received. Terminating Nova...")
        QApplication.instance().quit()

    @pyqtSlot()
    def minimize_to_tray(self):
        """Hide window to tray."""
        self.window.hide()

    def _run_assistant(self, text):
        if not self.assistant:
            return
            
        # Use NLP Layered Assistant for all processing
        response = self.assistant.process(text)
        # Send response back to JS
        self.window.browser.page().runJavaScript(f"window.setNovaResponse({json.dumps(response)})")
        # Speak response
        powershell_tts(response)
        self.window.setStatus("NEURAL CORE ACTIVE", "#00d2ff")

class NovaWindow(QMainWindow):
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        
        # Window Setup
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1200, 800)
        
        # Center on screen
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

        # Web View
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)

        # Bridge
        self.bridge = NovaInterface(assistant, self)
        self.channel = QWebChannel()
        self.channel.registerObject("pyObj", self.bridge)
        self.browser.page().setWebChannel(self.channel)

        # Load HUD
        hud_path = SCRIPT_DIR / "nova_hud.html"
        self.browser.setUrl(QUrl.fromLocalFile(str(hud_path)))

        # Stats Timer
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(2000)

        # System Tray Support
        self.init_tray()

        # Voice Thread
        try:
            self.voice_thread = QThread()
            self.voice_worker = VoiceWorker(assistant)
            self.voice_worker.moveToThread(self.voice_thread)
            self.voice_thread.started.connect(self.voice_worker.run)
            self.voice_worker.command_detected.connect(self.handle_voice_command)
            self.voice_worker.status_changed.connect(self.setStatus)
            self.voice_thread.start()
        except:
            print("Voice recognition initialization failed.")

    def init_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        # Use a high-visibility dot as a placeholder icon if no .ico exists
        # In a real app, you'd provide nova_icon.ico
        icon_path = SCRIPT_DIR / "assets" / "nova_icon.png"
        if icon_path.exists():
            self.tray_icon.setIcon(QIcon(str(icon_path)))
        else:
            # Fallback for demonstration
            self.tray_icon.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        
        tray_menu = QMenu()
        show_action = QAction("Open Nova HUD", self)
        hide_action = QAction("Hide HUD", self)
        exit_action = QAction("Exit Nova", self)
        
        show_action.triggered.connect(self.show_hud)
        hide_action.triggered.connect(self.hide)
        exit_action.triggered.connect(QApplication.instance().quit)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addSeparator()
        tray_menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_clicked)
        self.tray_icon.show()
        self.tray_icon.setToolTip("Nova AI - Always Listening")

    def tray_clicked(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_hud()

    def show_hud(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def handle_voice_command(self, cmd):
        self.browser.page().runJavaScript(f"addMessage({json.dumps(cmd)}, 'user')")
        # Ensure HUD is visible when voice command detected
        self.show_hud()
        self.bridge.process_input(cmd)

    def setStatus(self, status, color):
        self.browser.page().runJavaScript(f"window.setStatus({json.dumps(status)}, {json.dumps(color)})")

    def update_stats(self):
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            bat = psutil.sensors_battery().percent if psutil.sensors_battery() else 100
            uptime = str(datetime.now().strftime("%H:%M:%S"))
            
            habits_count = 0
            if self.assistant and self.assistant.learning:
                habits_count = len(self.assistant.learning.habits)

            stats = {
                "cpu": cpu,
                "mem": mem,
                "bat": bat,
                "uptime": uptime,
                "habits": habits_count
            }
            self.browser.page().runJavaScript(f"window.updateStats({json.dumps(stats)})")
        except: pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide() # Minimize to tray instead of closing

def main():
    if not GUI_AVAILABLE:
        print("Error: PyQt6 or PyQt6-WebEngine not installed. Install them to use the HUD.")
        return

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False) # Keep running in tray
    
    print("Core Initializing...")
    assistant = None
    if NovaLayeredAssistant:
        assistant = NovaLayeredAssistant(user_name="Boss")
    
    window = NovaWindow(assistant)
    window.show()
    print("Nova OS Interface Loaded in System Tray.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
