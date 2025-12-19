
import psutil
import time
from datetime import datetime

class SystemMonitor:
    """Core logic for gathering system metrics."""
    
    def __init__(self, cpu_threshold=80.0, mem_threshold=80.0):
        self.cpu_threshold = cpu_threshold
        self.mem_threshold = mem_threshold
    
    def get_metrics(self):
        """Gather current CPU and Memory metrics."""
        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory().percent
        
        status = "NORMAL"
        if cpu > self.cpu_threshold or mem > self.mem_threshold:
            status = "CRITICAL"
        elif cpu > self.cpu_threshold / 2 or mem > self.mem_threshold / 2:
            status = "WARNING"
            
        return {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "cpu": cpu,
            "memory": mem,
            "status": status
        }
