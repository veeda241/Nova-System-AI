#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════╗
║              NOVA COMPUTER CONTROL MODULE                     ║
║         Full System Control via Voice Commands                ║
╠═══════════════════════════════════════════════════════════════╣
║  Features:                                                    ║
║    • Open any application by name                             ║
║    • Close running applications                               ║
║    • Web searches (Google, YouTube, Wikipedia)                ║
║    • System commands (shutdown, restart, lock, sleep)         ║
║    • Volume control                                           ║
║    • File/folder operations                                   ║
║    • Screenshot                                               ║
║    • Open websites                                            ║
╚═══════════════════════════════════════════════════════════════╝
"""

import os
import subprocess
import webbrowser
import platform
from typing import Optional, Tuple
import re

# Common application mappings for Windows
APP_ALIASES = {
    # Browsers
    "chrome": "chrome",
    "google chrome": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "brave": "brave",
    
    # Microsoft Office
    "word": "winword",
    "microsoft word": "winword",
    "excel": "excel",
    "microsoft excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    "onenote": "onenote",
    "teams": "teams",
    
    # Development
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "visual studio": "devenv",
    "notepad": "notepad",
    "notepad++": "notepad++",
    "sublime": "sublime_text",
    "pycharm": "pycharm64",
    "intellij": "idea64",
    "android studio": "studio64",
    
    # System
    "file explorer": "explorer",
    "explorer": "explorer",
    "files": "explorer",
    "task manager": "taskmgr",
    "control panel": "control",
    "settings": "ms-settings:",
    "cmd": "cmd",
    "command prompt": "cmd",
    "terminal": "wt",
    "powershell": "powershell",
    "calculator": "calc",
    "paint": "mspaint",
    "snipping tool": "snippingtool",
    
    # Media
    "spotify": "spotify",
    "vlc": "vlc",
    "media player": "wmplayer",
    "windows media player": "wmplayer",
    "photos": "ms-photos:",
    
    # Communication
    "discord": "discord",
    "slack": "slack",
    "zoom": "zoom",
    "skype": "skype",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    
    # Gaming
    "steam": "steam",
    "epic games": "EpicGamesLauncher",
    
    # Others
    "obs": "obs64",
    "obs studio": "obs64",
    "blender": "blender",
    "photoshop": "photoshop",
    "premiere": "premiere",
    "after effects": "afterfx",
    "figma": "figma",
}

# Website shortcuts
WEBSITES = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "twitter": "https://twitter.com",
    "x": "https://twitter.com",
    "facebook": "https://facebook.com",
    "linkedin": "https://linkedin.com",
    "reddit": "https://reddit.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "amazon": "https://amazon.com",
    "netflix": "https://netflix.com",
    "spotify": "https://open.spotify.com",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
    "wikipedia": "https://wikipedia.org",
}


class NovaControl:
    """Nova Computer Control - Full system automation."""
    
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
    
    # ===================== APP CONTROL =====================
    
    def open_app(self, app_name: str) -> Tuple[bool, str]:
        """Open an application by name."""
        app_name_lower = app_name.lower().strip()
        
        # Check aliases
        exe_name = APP_ALIASES.get(app_name_lower, app_name_lower)
        
        try:
            if self.is_windows:
                # Handle special URIs (like ms-settings:)
                if exe_name.endswith(':'):
                    os.startfile(exe_name)
                    return True, f"Opening {app_name}"
                
                # Try direct start
                subprocess.Popen(
                    f'start "" "{exe_name}"',
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return True, f"Opening {app_name}"
            else:
                subprocess.Popen([exe_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True, f"Opening {app_name}"
                
        except Exception as e:
            # Try searching in Start Menu
            try:
                subprocess.Popen(
                    f'powershell -Command "Start-Process \'{app_name}\'"',
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return True, f"Opening {app_name}"
            except:
                return False, f"Could not open {app_name}: {e}"
    
    def close_app(self, app_name: str) -> Tuple[bool, str]:
        """Close an application by name."""
        app_name_lower = app_name.lower().strip()
        
        # Get process name
        exe_name = APP_ALIASES.get(app_name_lower, app_name_lower)
        if not exe_name.endswith('.exe'):
            exe_name += '.exe'
        
        try:
            if self.is_windows:
                # Kill process
                result = subprocess.run(
                    f'taskkill /IM "{exe_name}" /F',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return True, f"Closed {app_name}"
                else:
                    # Try with original name
                    result = subprocess.run(
                        f'taskkill /IM "{app_name}.exe" /F',
                        shell=True,
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        return True, f"Closed {app_name}"
                    return False, f"Could not find {app_name} running"
            else:
                subprocess.run(['pkill', '-f', app_name], capture_output=True)
                return True, f"Closed {app_name}"
                
        except Exception as e:
            return False, f"Error closing {app_name}: {e}"
    
    # ===================== WEB CONTROL =====================
    
    def open_website(self, url_or_name: str) -> Tuple[bool, str]:
        """Open a website."""
        name_lower = url_or_name.lower().strip()
        
        # Check shortcuts
        url = WEBSITES.get(name_lower)
        if not url:
            # Check if it's already a URL
            if name_lower.startswith(('http://', 'https://', 'www.')):
                url = url_or_name if url_or_name.startswith('http') else f'https://{url_or_name}'
            else:
                url = f'https://{url_or_name}.com'
        
        try:
            webbrowser.open(url)
            return True, f"Opening {url_or_name}"
        except Exception as e:
            return False, f"Could not open website: {e}"
    
    def google_search(self, query: str) -> Tuple[bool, str]:
        """Search Google."""
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        webbrowser.open(url)
        return True, f"Searching Google for: {query}"
    
    def youtube_search(self, query: str) -> Tuple[bool, str]:
        """Search YouTube."""
        url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        webbrowser.open(url)
        return True, f"Searching YouTube for: {query}"
    
    def wikipedia_search(self, query: str) -> Tuple[bool, str]:
        """Search Wikipedia."""
        url = f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}"
        webbrowser.open(url)
        return True, f"Opening Wikipedia: {query}"
    
    # ===================== SYSTEM CONTROL =====================
    
    def system_command(self, command: str) -> Tuple[bool, str]:
        """Execute system commands."""
        cmd_lower = command.lower().strip()
        
        if self.is_windows:
            if cmd_lower in ['shutdown', 'shut down', 'power off']:
                os.system('shutdown /s /t 60')
                return True, "Shutting down in 60 seconds. Say 'cancel shutdown' to abort."
            
            elif cmd_lower in ['restart', 'reboot']:
                os.system('shutdown /r /t 60')
                return True, "Restarting in 60 seconds. Say 'cancel shutdown' to abort."
            
            elif cmd_lower in ['cancel shutdown', 'abort shutdown']:
                os.system('shutdown /a')
                return True, "Shutdown cancelled."
            
            elif cmd_lower in ['lock', 'lock screen', 'lock computer']:
                os.system('rundll32.exe user32.dll,LockWorkStation')
                return True, "Locking computer."
            
            elif cmd_lower in ['sleep', 'hibernate']:
                os.system('rundll32.exe powrprof.dll,SetSuspendState 0,1,0')
                return True, "Going to sleep."
            
            elif cmd_lower in ['screenshot', 'take screenshot']:
                os.system('snippingtool')
                return True, "Opening snipping tool for screenshot."
            
        return False, f"Unknown system command: {command}"
    
    def volume_control(self, action: str) -> Tuple[bool, str]:
        """Control system volume."""
        action_lower = action.lower().strip()
        
        if self.is_windows:
            try:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                
                current = volume.GetMasterVolumeLevelScalar()
                
                if action_lower in ['mute', 'silence']:
                    volume.SetMute(1, None)
                    return True, "Volume muted."
                
                elif action_lower in ['unmute']:
                    volume.SetMute(0, None)
                    return True, "Volume unmuted."
                
                elif action_lower in ['up', 'increase', 'louder']:
                    new_vol = min(1.0, current + 0.1)
                    volume.SetMasterVolumeLevelScalar(new_vol, None)
                    return True, f"Volume increased to {int(new_vol * 100)}%"
                
                elif action_lower in ['down', 'decrease', 'quieter', 'lower']:
                    new_vol = max(0.0, current - 0.1)
                    volume.SetMasterVolumeLevelScalar(new_vol, None)
                    return True, f"Volume decreased to {int(new_vol * 100)}%"
                
                elif action_lower in ['max', 'maximum', 'full']:
                    volume.SetMasterVolumeLevelScalar(1.0, None)
                    return True, "Volume set to maximum."
                
                elif action_lower in ['min', 'minimum']:
                    volume.SetMasterVolumeLevelScalar(0.1, None)
                    return True, "Volume set to minimum."
                    
            except ImportError:
                # Use nircmd as fallback
                if action_lower in ['up', 'increase', 'louder']:
                    os.system('nircmd.exe changesysvolume 6553')
                    return True, "Volume increased."
                elif action_lower in ['down', 'decrease', 'quieter']:
                    os.system('nircmd.exe changesysvolume -6553')
                    return True, "Volume decreased."
                elif action_lower == 'mute':
                    os.system('nircmd.exe mutesysvolume 1')
                    return True, "Volume muted."
                elif action_lower == 'unmute':
                    os.system('nircmd.exe mutesysvolume 0')
                    return True, "Volume unmuted."
            except Exception as e:
                return False, f"Volume control error: {e}"
        
        return False, "Volume control not available."
    
    # ===================== FILE OPERATIONS =====================
    
    def open_folder(self, path: str) -> Tuple[bool, str]:
        """Open a folder in file explorer."""
        # Handle common folders
        folder_map = {
            'documents': os.path.expanduser('~/Documents'),
            'downloads': os.path.expanduser('~/Downloads'),
            'desktop': os.path.expanduser('~/Desktop'),
            'pictures': os.path.expanduser('~/Pictures'),
            'music': os.path.expanduser('~/Music'),
            'videos': os.path.expanduser('~/Videos'),
            'home': os.path.expanduser('~'),
        }
        
        folder = folder_map.get(path.lower(), path)
        
        if os.path.exists(folder):
            if self.is_windows:
                os.startfile(folder)
            else:
                subprocess.run(['xdg-open', folder])
            return True, f"Opening {path}"
        
        return False, f"Folder not found: {path}"
    
    # ===================== COMMAND PARSER =====================
    
    def parse_and_execute(self, command: str) -> Tuple[bool, str]:
        """Parse natural language command and execute."""
        cmd_lower = command.lower().strip()
        
        # Open app commands
        open_patterns = [
            r"open\s+(.+)",
            r"launch\s+(.+)",
            r"start\s+(.+)",
            r"run\s+(.+)",
        ]
        for pattern in open_patterns:
            match = re.match(pattern, cmd_lower)
            if match:
                target = match.group(1).strip()
                # Check if it's a website
                if target in WEBSITES or 'website' in cmd_lower or '.com' in target:
                    return self.open_website(target)
                # Check if it's a folder
                if target in ['documents', 'downloads', 'desktop', 'pictures', 'music', 'videos', 'home']:
                    return self.open_folder(target)
                # Otherwise open as app
                return self.open_app(target)
        
        # Close app commands
        close_patterns = [
            r"close\s+(.+)",
            r"quit\s+(.+)",
            r"exit\s+(.+)",
            r"kill\s+(.+)",
            r"terminate\s+(.+)",
        ]
        for pattern in close_patterns:
            match = re.match(pattern, cmd_lower)
            if match:
                return self.close_app(match.group(1).strip())
        
        # Search commands
        if cmd_lower.startswith('search ') or cmd_lower.startswith('google '):
            query = re.sub(r'^(search|google)\s+', '', cmd_lower)
            return self.google_search(query)
        
        if cmd_lower.startswith('youtube ') or 'on youtube' in cmd_lower:
            query = re.sub(r'^youtube\s+|on youtube', '', cmd_lower).strip()
            return self.youtube_search(query)
        
        if cmd_lower.startswith('wikipedia ') or 'on wikipedia' in cmd_lower:
            query = re.sub(r'^wikipedia\s+|on wikipedia', '', cmd_lower).strip()
            return self.wikipedia_search(query)
        
        # System commands
        system_cmds = ['shutdown', 'shut down', 'restart', 'reboot', 'lock', 'sleep', 
                       'hibernate', 'screenshot', 'cancel shutdown']
        for sys_cmd in system_cmds:
            if sys_cmd in cmd_lower:
                return self.system_command(sys_cmd)
        
        # Volume commands
        if 'volume' in cmd_lower or 'sound' in cmd_lower:
            if 'mute' in cmd_lower:
                return self.volume_control('mute')
            elif 'unmute' in cmd_lower:
                return self.volume_control('unmute')
            elif any(w in cmd_lower for w in ['up', 'increase', 'louder', 'higher']):
                return self.volume_control('up')
            elif any(w in cmd_lower for w in ['down', 'decrease', 'lower', 'quieter']):
                return self.volume_control('down')
            elif 'max' in cmd_lower or 'full' in cmd_lower:
                return self.volume_control('max')
        
        # Go to website
        if cmd_lower.startswith('go to '):
            target = cmd_lower.replace('go to ', '').strip()
            return self.open_website(target)
        
        return False, None


# Global instance
_nova_control: Optional[NovaControl] = None

def get_nova_control() -> NovaControl:
    """Get or create Nova Control singleton."""
    global _nova_control
    if _nova_control is None:
        _nova_control = NovaControl()
    return _nova_control


def nova_execute(command: str) -> Tuple[bool, str]:
    """Execute a voice command."""
    return get_nova_control().parse_and_execute(command)


# ===================== TEST =====================

if __name__ == "__main__":
    print("=" * 50)
    print("Nova Computer Control Test")
    print("=" * 50)
    
    control = get_nova_control()
    
    # Test commands
    test_commands = [
        "open chrome",
        "open notepad",
        "search python tutorials",
        "youtube music videos",
        "go to github",
    ]
    
    print("\nTest commands:")
    for cmd in test_commands:
        print(f"  '{cmd}' -> ", end="")
        success, msg = control.parse_and_execute(cmd)
        print(f"{'✅' if success else '❌'} {msg}")
