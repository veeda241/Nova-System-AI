import os
import shutil

# Directories to create
dirs = ['assets', 'tests', 'legacy', 'tools']
for d in dirs:
    if not os.path.exists(d):
        os.makedirs(d)

# Mapping: filename -> target directory
mapping = {
    "Screenshot 2025-12-16 094601.png": "assets",
    "Screenshot_2025-12-16_094601-removebg-preview.png": "assets",
    "Vyas.S Resume (1).pdf": "assets",
    "check_voice_deps.py": "tests",
    "master_test.py": "tests",
    "test_search.py": "tests",
    "voice_test.py": "tests",
    "nova.py": "legacy",
    "nova_agent.py": "legacy",
    "nova_automation.py": "legacy",
    "nova_ble.py": "legacy",
    "nova_bluetooth.py": "legacy",
    "nova_capabilities.py": "legacy",
    # "nova_ollama.py": "legacy", # User has it open, maybe skip or handle cautiously
    "nova_pm.py": "legacy",
    "nova_study.py": "legacy",
    "cleanup.py": "tools",
    "generate_docs.py": "tools",
    "app_cache.json": "tools"
}

for filename, target_dir in mapping.items():
    if os.path.exists(filename):
        try:
            shutil.move(filename, os.path.join(target_dir, filename))
            print(f"Moved {filename} to {target_dir}")
        except Exception as e:
            print(f"Failed to move {filename}: {e}")
