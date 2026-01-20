"""
Plugin: System Status
Description: Gets comprehensive system status
Author: Nova Auto-Generated
"""

import platform
import os
from datetime import datetime

def run(params: dict = None) -> str:
    """Get comprehensive system status."""
    try:
        status_lines = []
        
        # Basic info
        status_lines.append(f"🖥️ System Status - {datetime.now().strftime('%H:%M:%S')}")
        status_lines.append(f"• Device: {platform.node()}")
        status_lines.append(f"• OS: {platform.system()} {platform.release()}")
        
        # Try psutil for detailed info
        try:
            import psutil
            
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.5)
            cpu_count = psutil.cpu_count()
            status_lines.append(f"• CPU: {cpu_percent}% ({cpu_count} cores)")
            
            # Memory
            mem = psutil.virtual_memory()
            mem_used = mem.used / (1024**3)
            mem_total = mem.total / (1024**3)
            status_lines.append(f"• RAM: {mem_used:.1f}GB / {mem_total:.1f}GB ({mem.percent}%)")
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_free = disk.free / (1024**3)
            disk_total = disk.total / (1024**3)
            status_lines.append(f"• Disk: {disk_free:.1f}GB free of {disk_total:.1f}GB")
            
            # Battery
            battery = psutil.sensors_battery()
            if battery:
                charging = "⚡" if battery.power_plugged else "🔋"
                status_lines.append(f"• Battery: {charging} {battery.percent}%")
            
            # Uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            hours = int(uptime.total_seconds() // 3600)
            mins = int((uptime.total_seconds() % 3600) // 60)
            status_lines.append(f"• Uptime: {hours}h {mins}m")
            
        except ImportError:
            status_lines.append("• (Install psutil for detailed metrics)")
        
        return "\n".join(status_lines)
    
    except Exception as e:
        return f"Error getting system status: {e}"
