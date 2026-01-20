import subprocess
import os

def run_git(cmd):
    try:
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
        return result
    except Exception as e:
        return str(e)

output = ""
output += "--- Git Status ---\n"
output += run_git("git status")
output += "\n--- Git Remote ---\n"
output += run_git("git remote -v")
output += "\n--- Git Branch ---\n"
output += run_git("git rev-parse --abbrev-ref HEAD")

with open("git_check_results.txt", "w") as f:
    f.write(output)
