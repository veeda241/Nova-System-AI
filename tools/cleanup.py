import shutil
import os

target_dir = "nova_system"
os.makedirs(target_dir, exist_ok=True)

files_to_move = [
    "nova_agent.py",
    "nova_automation.py", 
    "nova_ble.py",
    "nova_bluetooth.py",
    "nova_ollama.py",
    "nova_pm.py",
    "nova_study.py"
]

for f in files_to_move:
    try:
        if os.path.exists(f):
            shutil.move(f, os.path.join(target_dir, f))
            print(f"Moved {f}")
        else:
            print(f"Skipped {f} (not found)")
    except Exception as e:
        print(f"Error moving {f}: {e}")
