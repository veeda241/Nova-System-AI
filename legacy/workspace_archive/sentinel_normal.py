
import psutil
import time
import os
from datetime import datetime

# --- NO-MODULE VERSION: ALL IN ONE FILE ---

class SystemMonitor:
    def __init__(self, cpu_threshold=80.0, mem_threshold=80.0):
        self.cpu_threshold = cpu_threshold
        self.mem_threshold = mem_threshold
    
    def get_metrics(self):
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        status = "NORMAL"
        if cpu > self.cpu_threshold or mem > self.mem_threshold:
            status = "CRITICAL"
        elif cpu > self.cpu_threshold / 2 or mem > self.mem_threshold / 2:
            status = "WARNING"
        return {"timestamp": datetime.now().strftime("%H:%M:%S"), "cpu": cpu, "memory": mem, "status": status}

class TerminalFormatter:
    COLORS = {"NORMAL": "\033[92m", "WARNING": "\033[93m", "CRITICAL": "\033[91m", "RESET": "\033[0m"}
    @staticmethod
    def format_log(metrics):
        color = TerminalFormatter.COLORS.get(metrics["status"], "")
        reset = TerminalFormatter.COLORS["RESET"]
        return (f"[{metrics['timestamp']}] "
                f"CPU: {color}{metrics['cpu']}%{reset} | "
                f"MEM: {color}{metrics['memory']}%{reset} | "
                f"STATUS: {color}{metrics['status']}{reset}")

def main():
    print("🚀 NovaSystemSentinel (Normal Mode) Starting...")
    print("Press Ctrl+C to stop.\n")
    
    monitor = SystemMonitor(70.0, 70.0)
    log_dir = "logs"
    if not os.path.exists(log_dir): os.makedirs(log_dir)
    log_file = os.path.join(log_dir, "sentinel_normal.log")
    
    try:
        while True:
            metrics = monitor.get_metrics()
            output = TerminalFormatter.format_log(metrics)
            print(output)
            with open(log_file, "a") as f:
                f.write(output.replace("\033[92m", "").replace("\033[93m", "").replace("\033[91m", "").replace("\033[0m", "") + "\n")
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n🛑 Sentinel Stopped.")

if __name__ == "__main__":
    main()
