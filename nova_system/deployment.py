#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Deployment - Deployment and Service Management
====================================================
Handles starting, stopping, and managing NOVA services.
"""

import os
import sys
import subprocess
import signal
import time
import json
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ServiceInfo:
    """Information about a running service."""
    name: str
    pid: int
    port: Optional[int]
    started_at: str
    status: str  # 'running', 'stopped', 'error'


class NovaDeployment:
    """Manages NOVA service deployment."""
    
    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.services: Dict[str, ServiceInfo] = {}
        self.state_file = os.path.join(self.project_root, "data", "deployment_state.json")
        self._load_state()
    
    def _load_state(self):
        """Load deployment state from file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    for name, info in data.items():
                        self.services[name] = ServiceInfo(**info)
            except:
                pass
    
    def _save_state(self):
        """Save deployment state to file."""
        os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        data = {name: vars(info) for name, info in self.services.items()}
        with open(self.state_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def check_ollama(self) -> bool:
        """Check if Ollama is running."""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def start_ollama(self) -> bool:
        """Start Ollama service."""
        if self.check_ollama():
            print("✅ Ollama is already running")
            return True
        
        try:
            if sys.platform == 'win32':
                subprocess.Popen(['ollama', 'serve'], 
                                creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen(['ollama', 'serve'], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL)
            
            # Wait for startup
            for _ in range(10):
                time.sleep(1)
                if self.check_ollama():
                    print("✅ Ollama started successfully")
                    return True
            
            print("❌ Ollama failed to start")
            return False
        except Exception as e:
            print(f"❌ Error starting Ollama: {e}")
            return False
    
    def start_api(self, port: int = 5000) -> Optional[ServiceInfo]:
        """Start the NOVA API service."""
        api_path = os.path.join(self.project_root, "interface", "api.py")
        
        if not os.path.exists(api_path):
            print(f"❌ API file not found: {api_path}")
            return None
        
        try:
            if sys.platform == 'win32':
                process = subprocess.Popen(
                    [sys.executable, "-B", api_path],
                    cwd=self.project_root,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                process = subprocess.Popen(
                    [sys.executable, "-B", api_path],
                    cwd=self.project_root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            
            service = ServiceInfo(
                name="nova-api",
                pid=process.pid,
                port=port,
                started_at=datetime.now().isoformat(),
                status="running"
            )
            self.services["nova-api"] = service
            self._save_state()
            print(f"✅ NOVA API started on port {port} (PID: {process.pid})")
            return service
        except Exception as e:
            print(f"❌ Error starting API: {e}")
            return None
    
    def start_gui(self) -> Optional[ServiceInfo]:
        """Start the NOVA GUI."""
        gui_path = os.path.join(self.project_root, "interface", "gui.py")
        
        if not os.path.exists(gui_path):
            print(f"❌ GUI file not found: {gui_path}")
            return None
        
        try:
            process = subprocess.Popen(
                [sys.executable, "-B", gui_path],
                cwd=self.project_root
            )
            
            service = ServiceInfo(
                name="nova-gui",
                pid=process.pid,
                port=None,
                started_at=datetime.now().isoformat(),
                status="running"
            )
            self.services["nova-gui"] = service
            self._save_state()
            print(f"✅ NOVA GUI started (PID: {process.pid})")
            return service
        except Exception as e:
            print(f"❌ Error starting GUI: {e}")
            return None
    
    def start_cli(self):
        """Start the NOVA CLI (interactive)."""
        cli_path = os.path.join(self.project_root, "interface", "cli.py")
        
        if not os.path.exists(cli_path):
            print(f"❌ CLI file not found: {cli_path}")
            return
        
        os.system(f'{sys.executable} -B "{cli_path}"')
    
    def stop_service(self, name: str) -> bool:
        """Stop a running service."""
        if name not in self.services:
            print(f"❌ Service '{name}' not found")
            return False
        
        service = self.services[name]
        try:
            if sys.platform == 'win32':
                subprocess.run(['taskkill', '/F', '/PID', str(service.pid)], 
                              capture_output=True)
            else:
                os.kill(service.pid, signal.SIGTERM)
            
            service.status = "stopped"
            self._save_state()
            print(f"✅ Stopped {name} (PID: {service.pid})")
            return True
        except Exception as e:
            print(f"❌ Error stopping {name}: {e}")
            return False
    
    def stop_all(self):
        """Stop all running services."""
        for name in list(self.services.keys()):
            self.stop_service(name)
    
    def status(self) -> Dict[str, str]:
        """Get status of all services."""
        status = {
            "ollama": "running" if self.check_ollama() else "stopped"
        }
        for name, service in self.services.items():
            status[name] = service.status
        return status
    
    def deploy_full_stack(self):
        """Deploy the full NOVA stack."""
        print("\n" + "="*50)
        print("  NOVA Full Stack Deployment")
        print("="*50 + "\n")
        
        # 1. Start Ollama
        print("[1/3] Starting Ollama...")
        self.start_ollama()
        
        # 2. Start API
        print("\n[2/3] Starting NOVA API...")
        self.start_api()
        time.sleep(2)
        
        # 3. Start GUI
        print("\n[3/3] Starting NOVA GUI...")
        self.start_gui()
        
        print("\n" + "="*50)
        print("  Deployment Complete!")
        print("="*50)
        print("\nStatus:")
        for name, stat in self.status().items():
            icon = "✅" if stat == "running" else "❌"
            print(f"  {icon} {name}: {stat}")


# Global deployment instance
_deployment = None

def get_deployment() -> NovaDeployment:
    """Get the global deployment instance."""
    global _deployment
    if _deployment is None:
        _deployment = NovaDeployment()
    return _deployment


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="NOVA Deployment Manager")
    parser.add_argument("command", choices=["start", "stop", "status", "deploy"],
                        help="Command to execute")
    parser.add_argument("--service", "-s", help="Service name (api, gui, cli)")
    
    args = parser.parse_args()
    deployment = get_deployment()
    
    if args.command == "status":
        print("\nNOVA Services Status:")
        for name, stat in deployment.status().items():
            icon = "✅" if stat == "running" else "❌"
            print(f"  {icon} {name}: {stat}")
    
    elif args.command == "deploy":
        deployment.deploy_full_stack()
    
    elif args.command == "start":
        if args.service == "api":
            deployment.start_api()
        elif args.service == "gui":
            deployment.start_gui()
        elif args.service == "cli":
            deployment.start_cli()
        elif args.service == "ollama":
            deployment.start_ollama()
        else:
            print("Specify --service: api, gui, cli, ollama")
    
    elif args.command == "stop":
        if args.service:
            deployment.stop_service(f"nova-{args.service}")
        else:
            deployment.stop_all()
