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
            os.path.expandvars('%LOCALAPPDATA%\\Temp')
        ]
        
        cleared = 0
        for temp_path in temp_paths:
            if os.path.exists(temp_path):
                for item in os.listdir(temp_path):
                    try:
                        item_path = os.path.join(temp_path, item)
                        if os.path.isfile(item_path):
                            os.remove(item_path)
                            cleared += 1
                        elif os.path.isdir(item_path):
                            shutil.rmtree(item_path)
                            cleared += 1
                    except:
                        pass
        
        return True, f"Cleared {cleared} temp items"
    
    def empty_recycle_bin(self) -> tuple:
        """Empty the recycle bin."""
        try:
            import ctypes
            ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x0007)
            return True, "Recycle bin emptied"
        except Exception as e:
            return False, str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# DESKTOP & WEB ORCHESTRATOR
# Coordinates desktop and web actions with workflows
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AutomationStep:
    """Represents a single automation step."""
    action: str
    params: Dict[str, Any] = field(default_factory=dict)
    wait_after: float = 0.5
    on_error: str = 'stop'  # 'stop', 'continue', 'retry'
    max_retries: int = 3

@dataclass
class AutomationWorkflow:
    """Represents an automation workflow."""
    name: str
    description: str
    steps: List[AutomationStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

class DesktopWebOrchestrator:
    """
    Orchestrates complex automation workflows across desktop and web.
    """
    
    def __init__(self):
        self.app_control = AppControlLayer()
        self.web_control = WebControlLayer()
        self.system = SystemInteractionEngine()
        self.hase = HumanActionSimulator()
        self.workflows: Dict[str, AutomationWorkflow] = {}
        self.running = False
        self.current_step = 0
    
    def create_workflow(self, name: str, description: str = "") -> AutomationWorkflow:
        """Create a new workflow."""
        workflow = AutomationWorkflow(name=name, description=description)
        self.workflows[name] = workflow
        return workflow
    
    def add_step(self, workflow_name: str, action: str, params: Dict = None, 
                 wait_after: float = 0.5) -> bool:
        """Add step to workflow."""
        if workflow_name not in self.workflows:
            return False
        
        step = AutomationStep(
            action=action,
            params=params or {},
            wait_after=wait_after
        )
        self.workflows[workflow_name].steps.append(step)
        return True
    
    def execute_workflow(self, workflow_name: str, callback: Callable = None) -> tuple:
        """Execute a workflow."""
        if workflow_name not in self.workflows:
            return False, f"Workflow not found: {workflow_name}"
        
        workflow = self.workflows[workflow_name]
        self.running = True
        results = []
        
        for i, step in enumerate(workflow.steps):
            if not self.running:
                return False, "Workflow stopped"
            
            self.current_step = i
            
            try:
                success, message = self._execute_step(step)
                results.append({'step': i, 'success': success, 'message': message})
                
                if callback:
                    callback(i, len(workflow.steps), success, message)
                
                if not success and step.on_error == 'stop':
                    self.running = False
                    return False, f"Workflow stopped at step {i}: {message}"
                
                time.sleep(step.wait_after)
                
            except Exception as e:
                results.append({'step': i, 'success': False, 'message': str(e)})
                if step.on_error == 'stop':
                    self.running = False
                    return False, f"Workflow error at step {i}: {e}"
        
        self.running = False
        return True, results
    
    def _execute_step(self, step: AutomationStep) -> tuple:
        """Execute a single automation step."""
        action = step.action.lower()
        params = step.params
        
        # App Control Actions
        if action == 'open_app':
            return self.app_control.open_app(params.get('app', ''))
        elif action == 'close_app':
            return self.app_control.close_app(params.get('app', ''))
        elif action == 'focus_window':
            return self.app_control.focus_window(params.get('title', ''))
        
        # Web Actions
        elif action == 'open_url':
            return self.web_control.open_url(params.get('url', ''))
        elif action == 'search_google':
            return self.web_control.search_google(params.get('query', ''))
        elif action == 'play_youtube':
            return self.web_control.play_youtube(params.get('query', ''))
        
        # System Actions
        elif action == 'set_volume':
            return self.system.set_volume(params.get('level', 50))
        elif action == 'mute':
            return self.system.mute()
        elif action == 'lock':
            return self.system.lock_screen()
        elif action == 'sleep':
            return self.system.sleep()
        
        # Mouse Actions
        elif action == 'click':
            return self.hase.click(params.get('x'), params.get('y'))
        elif action == 'move_mouse':
            return self.hase.move_mouse(params.get('x', 0), params.get('y', 0))
        elif action == 'type':
            return self.hase.type_text(params.get('text', ''))
        elif action == 'hotkey':
            return self.hase.hotkey(*params.get('keys', []))
        
        # Wait
        elif action == 'wait':
            time.sleep(params.get('seconds', 1))
            return True, f"Waited {params.get('seconds', 1)} seconds"
        
        else:
            return False, f"Unknown action: {action}"
    
    def stop_workflow(self):
        """Stop running workflow."""
        self.running = False
    
    def save_workflow(self, name: str, filepath: str) -> tuple:
        """Save workflow to file."""
        if name not in self.workflows:
            return False, "Workflow not found"
        
        try:
            workflow = self.workflows[name]
            data = {
                'name': workflow.name,
                'description': workflow.description,
                'steps': [
                    {
                        'action': s.action,
                        'params': s.params,
                        'wait_after': s.wait_after
                    }
                    for s in workflow.steps
                ]
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True, f"Saved to {filepath}"
        except Exception as e:
            return False, str(e)
    
    def load_workflow(self, filepath: str) -> tuple:
        """Load workflow from file."""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            workflow = self.create_workflow(data['name'], data.get('description', ''))
            
            for step_data in data.get('steps', []):
                step = AutomationStep(
                    action=step_data['action'],
                    params=step_data.get('params', {}),
                    wait_after=step_data.get('wait_after', 0.5)
                )
                workflow.steps.append(step)
            
            return True, workflow
        except Exception as e:
            return False, str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# UNIVERSAL AUTOMATION CONTROLLER
# Single interface for all automation capabilities
# ═══════════════════════════════════════════════════════════════════════════════

class UniversalAutomationController:
    """
    Unified interface for all automation capabilities.
    Provides simple methods for common automation tasks.
    """
    
    def __init__(self):
        self.hase = HumanActionSimulator()
        self.app = AppControlLayer()
        self.web = WebControlLayer()
        self.system = SystemInteractionEngine()
        self.orchestrator = DesktopWebOrchestrator()
        self.history: List[Dict] = []
    
    def execute(self, command: str) -> tuple:
        """Execute a natural language automation command."""
        cmd_lower = command.lower().strip()
        
        # Log command
        self.history.append({
            'command': command,
            'timestamp': datetime.now().isoformat()
        })
        
        # Parse and execute
        result = self._parse_and_execute(cmd_lower, command)
        self.history[-1]['result'] = result
        
        return result
    
    def execute_structured(self, action_dict: Dict) -> tuple:
        """Execute a structured automation command."""
        action = action_dict.get('action')
        
        if not action or action == 'chat':
            return True, action_dict.get('response', '')
            
        # Map to internal step execution
        # We access the orchestrator's _execute_step method directly
        # constructing a temporary AutomationStep
        step = AutomationStep(
            action=action,
            params={k: v for k, v in action_dict.items() if k != 'action'}
        )
        return self.orchestrator._execute_step(step)
    
    def _parse_and_execute(self, cmd_lower: str, original: str) -> tuple:
        """Parse command and execute appropriate action."""
        
        # App commands
        if cmd_lower.startswith('open '):
            app = cmd_lower.replace('open ', '').strip()
            return self.app.open_app(app)
        
        elif cmd_lower.startswith('close '):
            app = cmd_lower.replace('close ', '').strip()
            return self.app.close_app(app)
        
        elif cmd_lower.startswith('focus '):
            title = cmd_lower.replace('focus ', '').strip()
            return self.app.focus_window(title)
        
        # Web commands
        elif cmd_lower.startswith('go to ') or cmd_lower.startswith('navigate to '):
            url = cmd_lower.replace('go to ', '').replace('navigate to ', '').strip()
            if not url.startswith('http'):
                url = 'https://' + url
            return self.web.open_url(url)
        
        elif cmd_lower.startswith('search '):
            query = cmd_lower.replace('search ', '').strip()
            return self.web.search_google(query)
        
        elif cmd_lower.startswith('play '):
            query = cmd_lower.replace('play ', '').strip()
            return self.web.play_youtube(query)
        
        # System commands
        elif cmd_lower in ['mute', 'silence']:
            return self.system.mute()
        
        elif cmd_lower in ['unmute']:
            return self.system.unmute()
        
        elif 'volume' in cmd_lower:
            if 'up' in cmd_lower or '+' in cmd_lower:
                return self.system.set_volume(75)
            elif 'down' in cmd_lower or '-' in cmd_lower:
                return self.system.set_volume(25)
            elif 'max' in cmd_lower:
                return self.system.set_volume(100)
        
        elif 'brightness' in cmd_lower:
            if 'up' in cmd_lower or '+' in cmd_lower:
                return self.system.set_brightness(80)
            elif 'down' in cmd_lower or '-' in cmd_lower:
                return self.system.set_brightness(30)
        
        elif cmd_lower in ['lock', 'lock screen']:
            return self.system.lock_screen()
        
        elif cmd_lower in ['sleep']:
            return self.system.sleep()
        
        elif cmd_lower in ['shutdown', 'shut down']:
            return self.system.shutdown()
        
        elif cmd_lower in ['restart', 'reboot']:
            return self.system.restart()
        
        # Mouse commands
        elif cmd_lower.startswith('click'):
            return self.hase.click()
        
        elif cmd_lower.startswith('type '):
            text = original[5:].strip()  # Use original to preserve case
            return self.hase.type_text(text)
        
        elif cmd_lower.startswith('press '):
            key = cmd_lower.replace('press ', '').strip()
            return self.hase.press_key(key)
        
        # Screenshot
        elif 'screenshot' in cmd_lower:
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            return self.hase.screenshot(filename=filename)
        
        # Status
        elif cmd_lower in ['status', 'system status']:
            status = self.system.get_system_status()
            return True, status
        
        # Clear temp
        elif 'clear temp' in cmd_lower or 'clean temp' in cmd_lower:
            return self.system.clear_temp_files()
        
        # Clipboard
        elif cmd_lower.startswith('copy '):
            text = original[5:].strip()
            return self.system.copy_to_clipboard(text)
        
        elif cmd_lower in ['paste', 'get clipboard']:
            return self.system.get_clipboard()
        
        return False, f"Unknown command: {command}"
    
    def get_history(self) -> List[Dict]:
        """Get command history."""
        return self.history
    
    def clear_history(self):
        """Clear command history."""
        self.history = []


# ═══════════════════════════════════════════════════════════════════════════════
# UNIFIED CONTROL ENGINE (UCE)
# The main orchestrator that combines all engines
# ═══════════════════════════════════════════════════════════════════════════════

class UnifiedControlEngine:
    """
    The main Unified Control Engine that integrates all automation modules.
    Provides a central point for all automation capabilities.
    """
    
    def __init__(self):
        # Initialize all sub-engines
        self.hase = HumanActionSimulator()
        self.awcl_app = AppControlLayer()
        self.awcl_web = WebControlLayer()
        self.system = SystemInteractionEngine()
        self.orchestrator = DesktopWebOrchestrator()
        self.controller = UniversalAutomationController()
        
        # Engine status
        self.initialized = True
        self.version = "1.0.0"
        self.name = "NOVA Unified Control Engine"
    
    def execute(self, command: str) -> tuple:
        """Execute any automation command through the universal controller."""
        return self.controller.execute(command)
    
    def get_status(self) -> Dict:
        """Get status of all engines."""
        return {
            'name': self.name,
            'version': self.version,
            'initialized': self.initialized,
            'engines': {
                'hase': self.hase.pyautogui is not None,
                'app_control': True,
                'web_control': self.awcl_web.selenium is not None,
                'system': self.system.psutil is not None,
                'orchestrator': True
            },
            'system_status': self.system.get_system_status()
        }
    
    # === Quick Access Methods ===
    
    def open(self, app_or_url: str) -> tuple:
        """Open an app or URL."""
        if app_or_url.startswith('http') or '.' in app_or_url:
            return self.awcl_web.open_url(app_or_url)
        return self.awcl_app.open_app(app_or_url)
    
    def close(self, app: str) -> tuple:
        """Close an application."""
        return self.awcl_app.close_app(app)
    
    def click(self, x: int = None, y: int = None) -> tuple:
        """Click at position."""
        return self.hase.click(x, y)
    
    def type_text(self, text: str) -> tuple:
        """Type text."""
        return self.hase.type_text(text)
    
    def hotkey(self, *keys) -> tuple:
        """Press hotkey combination."""
        return self.hase.hotkey(*keys)
    
    def volume(self, level: int) -> tuple:
        """Set volume."""
        return self.system.set_volume(level)
    
    def brightness(self, level: int) -> tuple:
        """Set brightness."""
        return self.system.set_brightness(level)
    
    def lock(self) -> tuple:
        """Lock screen."""
        return self.system.lock_screen()
    
    def sleep(self) -> tuple:
        """Put system to sleep."""
        return self.system.sleep()
    
    def screenshot(self, filename: str = None) -> tuple:
        """Take screenshot."""
        return self.hase.screenshot(filename=filename)
    
    def search(self, query: str) -> tuple:
        """Search Google."""
        return self.awcl_web.search_google(query)
    
    def play(self, query: str) -> tuple:
        """Play on YouTube."""
        return self.awcl_web.play_youtube(query)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORTS & INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

# Create global instances for easy access
UCE = UnifiedControlEngine()
HASE = UCE.hase
AWCL_APP = UCE.awcl_app
AWCL_WEB = UCE.awcl_web
SYSTEM = UCE.system
ORCHESTRATOR = UCE.orchestrator
CONTROLLER = UCE.controller


def get_automation_status():
    """Get status of all automation engines."""
    return UCE.get_status()


def quick_command(command: str) -> tuple:
    """Execute a quick automation command."""
    return UCE.execute(command)


# CLI Test
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  NOVA AUTOMATION ENGINES - TEST")
    print("="*60)
    
    status = get_automation_status()
    print(f"\n  Engine: {status['name']} v{status['version']}")
    print("\n  Modules Status:")
    for engine, available in status['engines'].items():
        icon = "✅" if available else "❌"
        print(f"    {icon} {engine}")
    
    print("\n  System:")
    sys_status = status['system_status']
    print(f"    Platform: {sys_status.get('platform', 'N/A')}")
    print(f"    CPU: {sys_status.get('cpu_percent', 'N/A')}%")
    
    print("\n" + "="*60)
    print("  Type 'help' for available commands, 'exit' to quit")
    print("="*60 + "\n")
    
    while True:
        try:
            cmd = input("NOVA-AUTO> ").strip()
            if not cmd:
                continue
            if cmd.lower() in ['exit', 'quit']:
                break
            if cmd.lower() == 'help':
                print("""
  Available Commands:
  -------------------
  open <app>          - Open application
  close <app>         - Close application
  go to <url>         - Open URL
  search <query>      - Search Google
  play <query>        - Play on YouTube
  volume <0-100>      - Set volume
  brightness <0-100>  - Set brightness
  mute / unmute       - Mute/unmute
  lock                - Lock screen
  sleep               - Sleep system
  screenshot          - Take screenshot
  status              - System status
  clear temp          - Clear temp files
  type <text>         - Type text
  click               - Mouse click
  exit                - Exit
                """)
                continue
            
            success, result = quick_command(cmd)
            if success:
                print(f"  ✅ {result}")
            else:
                print(f"  ❌ {result}")
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\n  Goodbye!\n")
