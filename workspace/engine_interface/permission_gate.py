
import os
import subprocess
import psutil

class PermissionGate:
    """
    The Safety-First layer. Enforces human-in-the-loop for all system actions.
    Separates the 'Doing' from the 'Thinking'.
    """
    
    @staticmethod
    def ask_permission(intent_name, confidence):
        """Display intent and confidence, then wait for explicit y/n."""
        print(f"\n🛡️  [PERMISSION REQUEST]")
        print(f"Detected Intent: {intent_name}")
        print(f"Confidence: {confidence*100:.2f}%")
        
        choice = input(f"Confirm execution of {intent_name}? (y/n): ").lower().strip()
        return choice == 'y'

    @staticmethod
    def execute_intent(intent_id):
        """Safely map intent IDs to system library calls."""
        try:
            if intent_id == 0: # LOCK_SYSTEM
                print("🔒 Locking system...")
                subprocess.run("rundll32.exe user32.dll,LockWorkStation", shell=True)
            elif intent_id == 1: # VOLUME_UP
                print("🔊 Increasing volume...")
                # Simplified volume up via powershell
                subprocess.run('powershell (New-Object -ComObject WScript.Shell).SendKeys([char]175)', shell=True)
            elif intent_id == 2: # VOLUME_DOWN
                print("🔉 Decreasing volume...")
                # Simplified volume down via powershell
                subprocess.run('powershell (New-Object -ComObject WScript.Shell).SendKeys([char]174)', shell=True)
            elif intent_id == 3: # SYSTEM_STATUS
                print("📊 Gathering system status...")
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory().percent
                print(f"Status: CPU {cpu}% | MEM {mem}%")
            else:
                print("⚠️  Unknown intent or No Action required.")
        except Exception as e:
            print(f"❌ Execution error: {e}")
