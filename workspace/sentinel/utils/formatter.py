
class TerminalFormatter:
    """Utility for styling terminal output."""
    
    COLORS = {
        "NORMAL": "\033[92m",   # Green
        "WARNING": "\033[93m",  # Yellow
        "CRITICAL": "\033[91m", # Red
        "RESET": "\033[0m"
    }
    
    @staticmethod
    def format_log(metrics):
        """Format metrics for terminal display."""
        color = TerminalFormatter.COLORS.get(metrics["status"], "")
        reset = TerminalFormatter.COLORS["RESET"]
        
        return (f"[{metrics['timestamp']}] "
                f"CPU: {color}{metrics['cpu']}%{reset} | "
                f"MEM: {color}{metrics['memory']}%{reset} | "
                f"STATUS: {color}{metrics['status']}{reset}")
