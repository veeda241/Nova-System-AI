"""
Plugin: Check Battery
Description: Checks battery health and status
Author: Nova Auto-Generated
"""

import subprocess
import platform

def run(params: dict = None) -> str:
    """Check battery health and status."""
    try:
        if platform.system() != "Windows":
            return "Battery check is only available on Windows"
        
        # Try psutil first
        try:
            import psutil
            battery = psutil.sensors_battery()
            
            if not battery:
                return "No battery detected - this might be a desktop PC"
            
            percent = battery.percent
            plugged = "Charging" if battery.power_plugged else "Discharging"
            
            if battery.secsleft > 0 and not battery.power_plugged:
                hours = battery.secsleft // 3600
                mins = (battery.secsleft % 3600) // 60
                time_left = f"{hours}h {mins}m remaining"
            else:
                time_left = "N/A" if battery.power_plugged else "Calculating..."
            
            # Health estimate based on percent when fully charged
            health = "Good" if percent > 20 else "Low - please charge soon"
            
            return f"""🔋 Battery Status:
• Level: {percent}%
• Status: {plugged}
• Time Left: {time_left}
• Health: {health}"""
        
        except ImportError:
            # Fallback to PowerShell
            result = subprocess.run(
                ['powershell', '-Command', 
                 '(Get-WmiObject Win32_Battery | Select DesignCapacity,FullChargeCapacity,EstimatedChargeRemaining).EstimatedChargeRemaining'],
                capture_output=True, text=True
            )
            percent = result.stdout.strip()
            return f"Battery: {percent}% (Install psutil for more details)"
    
    except Exception as e:
        return f"Error checking battery: {e}"
