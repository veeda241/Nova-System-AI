
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
                # Send 25 volume up key presses (each is ~2% on Windows) = ~50% increase
                subprocess.run('powershell "$wsh = New-Object -ComObject WScript.Shell; for($i=0; $i -lt 25; $i++) { $wsh.SendKeys([char]175) }"', shell=True)
            elif intent_id == 2: # VOLUME_DOWN
                print("🔉 Decreasing volume...")
                # Send 25 volume down key presses = ~50% decrease
                subprocess.run('powershell "$wsh = New-Object -ComObject WScript.Shell; for($i=0; $i -lt 25; $i++) { $wsh.SendKeys([char]174) }"', shell=True)
            elif intent_id == 3: # SYSTEM_STATUS
                print("📊 Gathering system status...")
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory().percent
                print(f"Status: CPU {cpu}% | MEM {mem}%")
            elif intent_id == 5: # SHUTDOWN_SYSTEM
                print("🛑 Shutting down system...")
                os.system("shutdown /s /t 5")
                print("✅ Shutdown scheduled in 5 seconds (use 'shutdown /a' to abort)")
            elif intent_id == 6: # RESTART_SYSTEM
                print("🔄 Restarting system...")
                os.system("shutdown /r /t 5")
                print("✅ Restart scheduled in 5 seconds (use 'shutdown /a' to abort)")
            elif intent_id == 7: # SLEEP_SYSTEM
                print("🌙 Putting system to sleep...")
                # rundll32.exe powrprof.dll,SetSuspendState 0,1,0
                # Note: This might hibernate if Hibernation is enabled and Sleep is not.
                os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
                print("✅ Sleep command sent.")
            else:
                print("⚠️  Unknown intent or No Action required.")
        except Exception as e:
            print(f"❌ Execution error: {e}")
