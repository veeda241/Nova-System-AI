#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Automation Engines
========================
Complete automation suite for Nova CLI including:
- Unified Control Engine (UCE)
- Application & Web Control Layer (AWCL)
- System Interaction Engine
- Desktop & Web Orchestrator
- Universal Automation Controller
- Human-Action Simulation Engine
"""

import os
import sys
import time
import json
import subprocess
import platform
import threading
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# ═══════════════════════════════════════════════════════════════════════════════
# HUMAN-ACTION SIMULATION ENGINE (HASE)
# Simulates mouse movements, clicks, keyboard input like a human
# ═══════════════════════════════════════════════════════════════════════════════

class HumanActionSimulator:
    """
    Simulates human-like mouse and keyboard actions.
    Uses pyautogui for cross-platform automation.
    """
    
    def __init__(self):
        self.pyautogui = None
        self.keyboard = None
        self.mouse = None
        self._init_libraries()
    
    def _init_libraries(self):
        """Initialize automation libraries."""
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
            self.pyautogui = pyautogui
        except ImportError:
            pass
        
        try:
            from pynput import keyboard, mouse
            self.keyboard = keyboard
            self.mouse = mouse
        except ImportError:
            pass
    
    def move_mouse(self, x: int, y: int, duration: float = 0.5, human_like: bool = True):
        """Move mouse to position with optional human-like movement."""
        if not self.pyautogui:
            return False, "pyautogui not installed"
        
        try:
            if human_like:
                # Human-like movement with slight randomness
                import random
                steps = max(10, int(duration * 50))
                current_x, current_y = self.pyautogui.position()
                
                for i in range(steps):
                    progress = (i + 1) / steps
                    # Ease-in-out curve
                    ease = progress * progress * (3 - 2 * progress)
                    
                    new_x = current_x + (x - current_x) * ease + random.randint(-2, 2)
                    new_y = current_y + (y - current_y) * ease + random.randint(-2, 2)
                    
                    self.pyautogui.moveTo(new_x, new_y, _pause=False)
                    time.sleep(duration / steps)
                
                self.pyautogui.moveTo(x, y)
            else:
                self.pyautogui.moveTo(x, y, duration=duration)
            
            return True, f"Mouse moved to ({x}, {y})"
        except Exception as e:
            return False, str(e)
    
    def click(self, x: Optional[int] = None, y: Optional[int] = None, 
              button: str = 'left', clicks: int = 1, interval: float = 0.1):
        """Perform mouse click."""
        if not self.pyautogui:
            return False, "pyautogui not installed"
        
        try:
            self.pyautogui.click(x=x, y=y, button=button, clicks=clicks, interval=interval)
            return True, f"Clicked {button} button {clicks} time(s)"
        except Exception as e:
            return False, str(e)
    
    def double_click(self, x: Optional[int] = None, y: Optional[int] = None):
        """Perform double click."""
        return self.click(x, y, clicks=2)
    
    def right_click(self, x: Optional[int] = None, y: Optional[int] = None):
        """Perform right click."""
        return self.click(x, y, button='right')
    
    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5):
        """Drag from one position to another."""
        if not self.pyautogui:
            return False, "pyautogui not installed"
        
        try:
            self.pyautogui.moveTo(start_x, start_y)
            self.pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)
            return True, f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})"
        except Exception as e:
            return False, str(e)
    
    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None):
        """Scroll mouse wheel."""
        if not self.pyautogui:
            return False, "pyautogui not installed"
        
        try:
            self.pyautogui.scroll(clicks, x=x, y=y)
            return True, f"Scrolled {clicks} clicks"
        except Exception as e:
            return False, str(e)
    
    def type_text(self, text: str, interval: float = 0.05, human_like: bool = True):
        """Type text with optional human-like timing."""
        if not self.pyautogui:
            return False, "pyautogui not installed"
        
        try:
            if human_like:
                import random
                for char in text:
                    self.pyautogui.write(char, interval=0)
                    time.sleep(interval + random.uniform(-0.02, 0.05))
            else:
                self.pyautogui.write(text, interval=interval)
            
            return True, f"Typed: {text[:50]}..."
        except Exception as e:
            return False, str(e)
    
    def press_key(self, key: str):
        """Press a single key."""
        if not self.pyautogui:
            return False, "pyautogui not installed"
        
        try:
            self.pyautogui.press(key)
            return True, f"Pressed: {key}"
        except Exception as e:
            return False, str(e)
    
    def hotkey(self, *keys):
        """Press key combination (e.g., ctrl+c)."""
        if not self.pyautogui:
            return False, "pyautogui not installed"
        
        try:
            self.pyautogui.hotkey(*keys)
            return True, f"Pressed hotkey: {'+'.join(keys)}"
        except Exception as e:
            return False, str(e)
    
    def screenshot(self, region: Optional[tuple] = None, filename: Optional[str] = None):
        """Take screenshot of screen or region."""
        if not self.pyautogui:
            return False, "pyautogui not installed"
        
        try:
            img = self.pyautogui.screenshot(region=region)
            if filename:
                img.save(filename)
                return True, f"Screenshot saved to {filename}"
            return True, img
        except Exception as e:
            return False, str(e)
    
    def locate_on_screen(self, image_path: str, confidence: float = 0.9):
        """Find image on screen and return position."""
        if not self.pyautogui:
            return False, "pyautogui not installed"
        
        try:
            location = self.pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = self.pyautogui.center(location)
                return True, {"x": center.x, "y": center.y, "region": location}
            return False, "Image not found on screen"
        except Exception as e:
            return False, str(e)
    
    def get_mouse_position(self):
        """Get current mouse position."""
        if not self.pyautogui:
            return False, "pyautogui not installed"
        
        try:
            pos = self.pyautogui.position()
            return True, {"x": pos.x, "y": pos.y}
        except Exception as e:
            return False, str(e)
    
    def get_screen_size(self):
        """Get screen dimensions."""
        if not self.pyautogui:
            return False, "pyautogui not installed"
        
        try:
            size = self.pyautogui.size()
            return True, {"width": size.width, "height": size.height}
        except Exception as e:
            return False, str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# APPLICATION & WEB CONTROL LAYER (AWCL)
# Controls desktop applications and web browsers
# ═══════════════════════════════════════════════════════════════════════════════

class AppControlLayer:
    """
    Controls desktop applications - open, close, focus, minimize, maximize.
    """
    
    # Common Windows application mappings
    APP_MAPPINGS = {
        'chrome': {'exe': 'chrome.exe', 'cmd': 'start chrome'},
        'firefox': {'exe': 'firefox.exe', 'cmd': 'start firefox'},
        'edge': {'exe': 'msedge.exe', 'cmd': 'start msedge'},
        'notepad': {'exe': 'notepad.exe', 'cmd': 'start notepad'},
        'calculator': {'exe': 'CalculatorApp.exe', 'cmd': 'start calc'},
        'vscode': {'exe': 'Code.exe', 'cmd': 'start code'},
        'explorer': {'exe': 'explorer.exe', 'cmd': 'start explorer'},
        'terminal': {'exe': 'WindowsTerminal.exe', 'cmd': 'start wt'},
        'cmd': {'exe': 'cmd.exe', 'cmd': 'start cmd'},
        'powershell': {'exe': 'powershell.exe', 'cmd': 'start powershell'},
        'spotify': {'exe': 'Spotify.exe', 'cmd': 'start spotify:'},
        'discord': {'exe': 'Discord.exe', 'cmd': 'start discord:'},
        'word': {'exe': 'WINWORD.EXE', 'cmd': 'start winword'},
        'excel': {'exe': 'EXCEL.EXE', 'cmd': 'start excel'},
        'powerpoint': {'exe': 'POWERPNT.EXE', 'cmd': 'start powerpnt'},
        'outlook': {'exe': 'OUTLOOK.EXE', 'cmd': 'start outlook'},
        'teams': {'exe': 'Teams.exe', 'cmd': 'start msteams:'},
        'slack': {'exe': 'slack.exe', 'cmd': 'start slack:'},
        'zoom': {'exe': 'Zoom.exe', 'cmd': 'start zoommtg:'},
        'paint': {'exe': 'mspaint.exe', 'cmd': 'start mspaint'},
        'photos': {'exe': 'Microsoft.Photos.exe', 'cmd': 'start ms-photos:'},
        'settings': {'exe': 'SystemSettings.exe', 'cmd': 'start ms-settings:'},
        'store': {'exe': 'WinStore.App.exe', 'cmd': 'start ms-windows-store:'},
        'vlc': {'exe': 'vlc.exe', 'cmd': 'start vlc'},
        'obs': {'exe': 'obs64.exe', 'cmd': 'start obs64'},
    }
    
    def __init__(self):
        self.running_apps = {}
        self._init_win32()
    
    def _init_win32(self):
        """Initialize Windows-specific libraries."""
        self.win32gui = None
        self.win32con = None
        self.win32process = None
        
        try:
            import win32gui
            import win32con
            import win32process
            self.win32gui = win32gui
            self.win32con = win32con
            self.win32process = win32process
        except ImportError:
            pass
    
    def open_app(self, app_name: str) -> tuple:
        """Open an application by name."""
        app_lower = app_name.lower().strip()
        
        # Check mappings first
        if app_lower in self.APP_MAPPINGS:
            cmd = self.APP_MAPPINGS[app_lower]['cmd']
            try:
                os.system(cmd)
                return True, f"Opened {app_name}"
            except Exception as e:
                return False, str(e)
        
        # Try generic start command
        try:
            os.system(f'start "" "{app_name}"')
            return True, f"Attempted to open {app_name}"
        except Exception as e:
            return False, str(e)
    
    def close_app(self, app_name: str, force: bool = False) -> tuple:
        """Close an application by name."""
        app_lower = app_name.lower().strip()
        
        # Get process name
        if app_lower in self.APP_MAPPINGS:
            exe = self.APP_MAPPINGS[app_lower]['exe']
        else:
            exe = f"{app_name}.exe"
        
        try:
            flag = '/f' if force else ''
            result = subprocess.run(
                f'taskkill {flag} /im {exe}',
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                return True, f"Closed {app_name}"
            return False, result.stderr or "App not found"
        except Exception as e:
            return False, str(e)
    
    def get_running_apps(self) -> List[Dict]:
        """Get list of running applications."""
        apps = []
        try:
            result = subprocess.run(
                'tasklist /fo csv /nh',
                shell=True, capture_output=True, text=True
            )
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.strip('"').split('","')
                    if len(parts) >= 5:
                        apps.append({
                            'name': parts[0],
                            'pid': parts[1],
                            'memory': parts[4]
                        })
        except:
            pass
        return apps
    
    def focus_window(self, title: str) -> tuple:
        """Bring window with given title to foreground."""
        if not self.win32gui:
            return False, "win32gui not available"
        
        try:
            def callback(hwnd, windows):
                if self.win32gui.IsWindowVisible(hwnd):
                    window_title = self.win32gui.GetWindowText(hwnd)
                    if title.lower() in window_title.lower():
                        windows.append(hwnd)
            
            windows = []
            self.win32gui.EnumWindows(callback, windows)
            
            if windows:
                hwnd = windows[0]
                self.win32gui.ShowWindow(hwnd, self.win32con.SW_RESTORE)
                self.win32gui.SetForegroundWindow(hwnd)
                return True, f"Focused window: {title}"
            return False, f"Window not found: {title}"
        except Exception as e:
            return False, str(e)
    
    def minimize_window(self, title: str) -> tuple:
        """Minimize window with given title."""
        if not self.win32gui:
            return False, "win32gui not available"
        
        try:
            def callback(hwnd, result):
                if title.lower() in self.win32gui.GetWindowText(hwnd).lower():
                    self.win32gui.ShowWindow(hwnd, self.win32con.SW_MINIMIZE)
                    result.append(True)
            
            result = []
            self.win32gui.EnumWindows(callback, result)
            
            if result:
                return True, f"Minimized: {title}"
            return False, f"Window not found: {title}"
        except Exception as e:
            return False, str(e)
    
    def maximize_window(self, title: str) -> tuple:
        """Maximize window with given title."""
        if not self.win32gui:
            return False, "win32gui not available"
        
        try:
            def callback(hwnd, result):
                if title.lower() in self.win32gui.GetWindowText(hwnd).lower():
                    self.win32gui.ShowWindow(hwnd, self.win32con.SW_MAXIMIZE)
                    result.append(True)
            
            result = []
            self.win32gui.EnumWindows(callback, result)
            
            if result:
                return True, f"Maximized: {title}"
            return False, f"Window not found: {title}"
        except Exception as e:
            return False, str(e)
    
    def list_windows(self) -> List[Dict]:
        """Get list of all visible windows."""
        windows = []
        
        if not self.win32gui:
            return windows
        
        try:
            def callback(hwnd, windows_list):
                if self.win32gui.IsWindowVisible(hwnd):
                    title = self.win32gui.GetWindowText(hwnd)
                    if title:
                        windows_list.append({
                            'hwnd': hwnd,
                            'title': title
                        })
            
            self.win32gui.EnumWindows(callback, windows)
        except:
            pass
        
        return windows


class WebControlLayer:
    """
    Controls web browsers - navigate, interact with pages, manage tabs.
    """
    
    def __init__(self):
        self.selenium = None
        self.driver = None
        self._init_selenium()
    
    def _init_selenium(self):
        """Initialize Selenium WebDriver."""
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.common.keys import Keys
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            self.selenium = {
                'webdriver': webdriver,
                'By': By,
                'Keys': Keys,
                'WebDriverWait': WebDriverWait,
                'EC': EC
            }
        except ImportError:
            pass
    
    def start_browser(self, browser: str = 'chrome', headless: bool = False) -> tuple:
        """Start a browser session."""
        if not self.selenium:
            # Fallback to os.system
            os.system(f'start {browser}')
            return True, f"Started {browser} (no Selenium)"
        
        try:
            webdriver = self.selenium['webdriver']
            
            if browser == 'chrome':
                options = webdriver.ChromeOptions()
                if headless:
                    options.add_argument('--headless')
                self.driver = webdriver.Chrome(options=options)
            elif browser == 'firefox':
                options = webdriver.FirefoxOptions()
                if headless:
                    options.add_argument('--headless')
                self.driver = webdriver.Firefox(options=options)
            elif browser == 'edge':
                options = webdriver.EdgeOptions()
                if headless:
                    options.add_argument('--headless')
                self.driver = webdriver.Edge(options=options)
            else:
                return False, f"Unknown browser: {browser}"
            
            return True, f"Started {browser} browser"
        except Exception as e:
            return False, str(e)
    
    def navigate(self, url: str) -> tuple:
        """Navigate to URL."""
        if not self.driver:
            # Fallback
            os.system(f'start "" "{url}"')
            return True, f"Opened {url} in default browser"
        
        try:
            self.driver.get(url)
            return True, f"Navigated to {url}"
        except Exception as e:
            return False, str(e)
    
    def open_url(self, url: str) -> tuple:
        """Open URL in default browser."""
        try:
            import webbrowser
            webbrowser.open(url)
            return True, f"Opened {url}"
        except Exception as e:
            return False, str(e)
    
    def search_google(self, query: str) -> tuple:
        """Search Google."""
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        return self.open_url(url)
    
    def search_youtube(self, query: str) -> tuple:
        """Search YouTube."""
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        return self.open_url(url)
    
    def play_youtube(self, query: str) -> tuple:
        """Play video on YouTube."""
        try:
            import pywhatkit
            pywhatkit.playonyt(query)
            return True, f"Playing: {query}"
        except ImportError:
            return self.search_youtube(query)
    
    def close_browser(self) -> tuple:
        """Close browser session."""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                return True, "Browser closed"
            except Exception as e:
                return False, str(e)
        return True, "No browser to close"


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM INTERACTION ENGINE
# Manages system-level interactions (volume, brightness, power, etc.)
# ═══════════════════════════════════════════════════════════════════════════════

class SystemInteractionEngine:
    """
    Handles all system-level interactions and controls.
    """
    
    def __init__(self):
        self.psutil = None
        self._init_psutil()
    
    def _init_psutil(self):
        """Initialize psutil for system monitoring."""
        try:
            import psutil
            self.psutil = psutil
        except ImportError:
            pass
    
    # === VOLUME CONTROL ===
    def set_volume(self, level: int) -> tuple:
        """Set system volume (0-100)."""
        level = max(0, min(100, level))
        
        try:
            # Try pycaw first
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level / 100, None)
            return True, f"Volume set to {level}%"
        except:
            # Fallback to nircmd or PowerShell
            try:
                os.system(f'nircmd.exe setsysvolume {int(level * 655.35)}')
                return True, f"Volume set to {level}%"
            except:
                return False, "Volume control not available"
    
    def mute(self) -> tuple:
        """Mute system volume."""
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMute(1, None)
            return True, "System muted"
        except:
            os.system('nircmd.exe mutesysvolume 1')
            return True, "System muted"
    
    def unmute(self) -> tuple:
        """Unmute system volume."""
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMute(0, None)
            return True, "System unmuted"
        except:
            os.system('nircmd.exe mutesysvolume 0')
            return True, "System unmuted"
    
    # === BRIGHTNESS CONTROL ===
    def set_brightness(self, level: int) -> tuple:
        """Set screen brightness (0-100)."""
        level = max(0, min(100, level))
        
        try:
            import screen_brightness_control as sbc
            sbc.set_brightness(level)
            return True, f"Brightness set to {level}%"
        except:
            # Fallback to PowerShell
            cmd = f'powershell "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"'
            os.system(cmd)
            return True, f"Brightness set to {level}%"
    
    def get_brightness(self) -> tuple:
        """Get current screen brightness."""
        try:
            import screen_brightness_control as sbc
            brightness = sbc.get_brightness()
            return True, brightness[0] if isinstance(brightness, list) else brightness
        except:
            return False, "Cannot get brightness"
    
    # === POWER CONTROL ===
    def lock_screen(self) -> tuple:
        """Lock the screen."""
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return True, "Screen locked"
        except Exception as e:
            return False, str(e)
    
    def sleep(self) -> tuple:
        """Put system to sleep."""
        os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
        return True, "System sleeping"
    
    def shutdown(self, delay: int = 0) -> tuple:
        """Shutdown the system."""
        os.system(f'shutdown /s /t {delay}')
        return True, f"Shutdown scheduled in {delay} seconds"
    
    def restart(self, delay: int = 0) -> tuple:
        """Restart the system."""
        os.system(f'shutdown /r /t {delay}')
        return True, f"Restart scheduled in {delay} seconds"
    
    def cancel_shutdown(self) -> tuple:
        """Cancel scheduled shutdown."""
        os.system('shutdown /a')
        return True, "Shutdown cancelled"
    
    def hibernate(self) -> tuple:
        """Hibernate the system."""
        os.system('shutdown /h')
        return True, "System hibernating"
    
    # === SYSTEM INFO ===
    def get_system_status(self) -> Dict:
        """Get comprehensive system status."""
        status = {
            'platform': platform.system(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
        }
        
        if self.psutil:
            status['cpu_percent'] = self.psutil.cpu_percent()
            status['memory'] = dict(self.psutil.virtual_memory()._asdict())
            status['disk'] = dict(self.psutil.disk_usage('/')._asdict())
            
            battery = self.psutil.sensors_battery()
            if battery:
                status['battery'] = {
                    'percent': battery.percent,
                    'charging': battery.power_plugged,
                    'time_left': battery.secsleft if battery.secsleft != -1 else None
                }
        
        return status
    
    def get_cpu_usage(self) -> float:
        """Get CPU usage percentage."""
        if self.psutil:
            return self.psutil.cpu_percent()
        return 0
    
    def get_memory_usage(self) -> Dict:
        """Get memory usage info."""
        if self.psutil:
            mem = self.psutil.virtual_memory()
            return {
                'total': mem.total,
                'available': mem.available,
                'percent': mem.percent,
                'used': mem.used
            }
        return {}
    
    def get_disk_usage(self, path: str = '/') -> Dict:
        """Get disk usage info."""
        if self.psutil:
            disk = self.psutil.disk_usage(path)
            return {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': disk.percent
            }
        return {}
    
    def get_battery_status(self) -> Dict:
        """Get battery status."""
        if self.psutil:
            battery = self.psutil.sensors_battery()
            if battery:
                return {
                    'percent': battery.percent,
                    'charging': battery.power_plugged,
                    'time_left': battery.secsleft
                }
        return {}
    
    # === NETWORK ===
    def get_ip_address(self) -> Dict:
        """Get IP addresses."""
        import socket
        
        result = {'local': None, 'public': None}
        
        try:
            hostname = socket.gethostname()
            result['local'] = socket.gethostbyname(hostname)
        except:
            pass
        
        try:
            import urllib.request
            result['public'] = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
        except:
            pass
        
        return result
    
    # === CLIPBOARD ===
    def copy_to_clipboard(self, text: str) -> tuple:
        """Copy text to clipboard."""
        try:
            import pyperclip
            pyperclip.copy(text)
            return True, "Copied to clipboard"
        except:
            # Fallback using PowerShell
            subprocess.run(['powershell', '-command', f'Set-Clipboard -Value "{text}"'], check=True)
            return True, "Copied to clipboard"
    
    def get_clipboard(self) -> tuple:
        """Get clipboard content."""
        try:
            import pyperclip
            return True, pyperclip.paste()
        except:
            result = subprocess.run(['powershell', '-command', 'Get-Clipboard'], capture_output=True, text=True)
            return True, result.stdout.strip()
    
    # === FILE OPERATIONS ===
    def clear_temp_files(self) -> tuple:
        """Clear temporary files."""
        import shutil
        temp_paths = [
            os.environ.get('TEMP', ''),
            os.environ.get('TMP', '')
        ]
        
        count = 0
        for path in temp_paths:
            if not path or not os.path.exists(path): continue
            
            for file in os.listdir(path):
                try:
                    full_path = os.path.join(path, file)
                    if os.path.isfile(full_path):
                        os.unlink(full_path)
                        count += 1
                except:
                    pass
        
        return True, f"Cleared {count} temporary files"

# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED CONTROL ENGINE (UCE)
# ═══════════════════════════════════════════════════════════════════════════════

class UnifiedControlEngine:
    """
    Central hub that unifies all automation engines.
    """
    
    def __init__(self):
        self.HASE = HumanActionSimulator()
        self.AWCL_APP = AppControlLayer()
        self.AWCL_WEB = WebControlLayer()
        self.SYSTEM = SystemInteractionEngine()
    
    def get_status(self) -> Dict:
        """Get status of all engines for Nova CLI."""
        return {
            "name": "Nova Unified Control Engine",
            "version": "2.0.0",
            "engines": {
                "HASE (Human Simulation)": self.HASE.pyautogui is not None if self.HASE else False,
                "AWCL-APP (Desktop)": self.AWCL_APP is not None,
                "AWCL-WEB (Browser)": self.AWCL_WEB.selenium is not None if self.AWCL_WEB else False,
                "SYSTEM (Core)": self.SYSTEM is not None
            },
            "system_info": self.SYSTEM.get_system_status() if self.SYSTEM else None
        }

# Initializing Engines
UCE = UnifiedControlEngine()
HASE = UCE.HASE
AWCL_APP = UCE.AWCL_APP
AWCL_WEB = UCE.AWCL_WEB
SYSTEM = UCE.SYSTEM
ORCHESTRATOR = UCE
CONTROLLER = UCE  # Alias

def get_automation_status():
    return UCE.get_status()

def quick_command(full_cmd):
    """
    Quickly execute an automation command from a full string.
    Supports: open <app>, close <app>, volume <X>, mute, lock, etc.
    """
    parts = full_cmd.lower().strip().split()
    if not parts:
        return False, "No command provided"
    
    cmd = parts[0]
    arg = " ".join(parts[1:]) if len(parts) > 1 else None
    
    if cmd == "mute":
        return SYSTEM.mute()
    elif cmd == "unmute":
        return SYSTEM.unmute()
    elif cmd == "lock":
        return SYSTEM.lock_screen()
    elif cmd == "sleep":
        return SYSTEM.sleep()
    elif cmd == "screenshot":
        return HASE.screenshot(filename="screenshot.png")
    elif cmd == "open" and arg:
        return AWCL_APP.open_app(arg)
    elif cmd == "close" and arg:
        return AWCL_APP.close_app(arg)
    elif cmd == "volume" and arg:
        try:
            return SYSTEM.set_volume(int(arg))
        except:
            return False, "Invalid volume"
    elif cmd == "brightness" and arg:
        try:
            return SYSTEM.set_brightness(int(arg))
        except:
            return False, "Invalid brightness"
    elif cmd == "go" and (arg.startswith("to ") or arg.startswith("http")):
        url = arg.replace("to ", "")
        return AWCL_WEB.open_url(url)
    elif cmd == "search" and arg:
        return AWCL_WEB.search_google(arg)
    elif cmd == "play" and arg:
        return AWCL_WEB.play_youtube(arg)
    elif cmd == "type" and arg:
        return HASE.type_text(arg)
    elif cmd == "status":
        return True, SYSTEM.get_system_status()
    elif cmd == "clear" and arg == "temp":
        return SYSTEM.clear_temp_files()
    
    return False, f"Unknown or incomplete command: {cmd}"
