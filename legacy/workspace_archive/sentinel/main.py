
import os
import sys
import time

# Add the current directory to path for modular imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.monitor import SystemMonitor
from utils.formatter import TerminalFormatter

def main():
    print("🚀 NovaSystemSentinel Starting...")
    print("Press Ctrl+C to stop.\n")
    
    monitor = SystemMonitor(cpu_threshold=70.0, mem_threshold=70.0)
    log_file = os.path.join(os.path.dirname(__file__), "logs", "monitor.log")
    
    try:
        while True:
            metrics = monitor.get_metrics()
            output = TerminalFormatter.format_log(metrics)
            print(output)
            
            # Persist to log file
            with open(log_file, "a") as f:
                f.write(output.replace("\033[92m", "").replace("\033[93m", "").replace("\033[91m", "").replace("\033[0m", "") + "\n")
            
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n🛑 Sentinel Stopped.")

if __name__ == "__main__":
    main()
