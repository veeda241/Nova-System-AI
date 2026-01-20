"""
Plugin: Clean Downloads
Description: Cleans old files from the Downloads folder
Author: Nova Auto-Generated
"""

import os
from pathlib import Path
from datetime import datetime, timedelta

def run(params: dict = None) -> str:
    """Clean old files from Downloads folder."""
    try:
        downloads = Path.home() / "Downloads"
        if not downloads.exists():
            return "Downloads folder not found"
        
        # Get parameters
        days = params.get("days", 30) if params else 30
        dry_run = params.get("dry_run", True) if params else True
        
        cutoff = datetime.now() - timedelta(days=days)
        old_files = []
        
        for file in downloads.iterdir():
            if file.is_file():
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                if mtime < cutoff:
                    old_files.append(file.name)
                    if not dry_run:
                        file.unlink()
        
        if not old_files:
            return f"No files older than {days} days found in Downloads."
        
        if dry_run:
            return f"Found {len(old_files)} files older than {days} days: {', '.join(old_files[:5])}{'...' if len(old_files) > 5 else ''}\nRun with dry_run=False to delete."
        else:
            return f"Deleted {len(old_files)} old files from Downloads."
    
    except Exception as e:
        return f"Error cleaning downloads: {e}"
