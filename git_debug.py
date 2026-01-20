import subprocess
import os

def run_git_cmd(cmd):
    print(f"Running: {cmd}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
        print("STDOUT:")
        print(result.stdout)
        print("STDERR:")
        print(result.stderr)
    except Exception as e:
        print(f"Error: {e}")

run_git_cmd("git status")
run_git_cmd("git log -n 5 --oneline")
