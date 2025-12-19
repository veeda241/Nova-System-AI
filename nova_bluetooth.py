#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOVA Bluetooth Server
Allows controlling NOVA from a phone via Bluetooth Serial (SPP)
"""

import os
import sys
import json
import threading
import time
import subprocess
from typing import Optional, Callable

# Try to import serial for Bluetooth COM port communication
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("Warning: pyserial not installed. Run: pip install pyserial")

class BluetoothServer:
    """
    Bluetooth Serial Port Profile (SPP) Server for NOVA.
    
    How it works:
    1. Pair your phone with your PC via Bluetooth
    2. This creates a virtual COM port on your PC
    3. Use a Bluetooth Terminal app on your phone to connect
    4. Send commands to NOVA and receive responses
    """
    
    def __init__(self, nova_instance=None):
        self.nova = nova_instance
        self.running = False
        self.serial_port: Optional[serial.Serial] = None
        self.thread: Optional[threading.Thread] = None
        self.message_handler: Optional[Callable] = None
        
    def find_bluetooth_ports(self) -> list:
        """Find available Bluetooth COM ports."""
        if not SERIAL_AVAILABLE:
            return []
        
        bluetooth_ports = []
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            # Bluetooth ports usually have "Bluetooth" or "SPP" in description
            desc_lower = port.description.lower()
            if any(keyword in desc_lower for keyword in ['bluetooth', 'spp', 'serial', 'bth']):
                bluetooth_ports.append({
                    'port': port.device,
                    'description': port.description,
                    'hwid': port.hwid
                })
        
        # Also return all COM ports as potential Bluetooth ports
        all_ports = [{
            'port': port.device,
            'description': port.description,
            'hwid': port.hwid
        } for port in ports]
        
        return bluetooth_ports if bluetooth_ports else all_ports
    
    def start(self, port: str = None, baud_rate: int = 9600) -> bool:
        """
        Start the Bluetooth server on specified COM port.
        
        Args:
            port: COM port name (e.g., 'COM5', '5', or list number '1'). If None, auto-detect.
            baud_rate: Baud rate for serial communication (default 9600)
        
        Returns:
            True if server started successfully
        """
        if not SERIAL_AVAILABLE:
            print("Error: pyserial not installed. Run: pip install pyserial")
            return False
        
        if self.running:
            print("Bluetooth server already running")
            return True
        
        # Get available ports for reference
        available_ports = self.find_bluetooth_ports()
        
        # Parse port input - handle various input formats
        if port is not None and port.strip():
            port = port.strip()
            
            # If user entered just a number, try to interpret it
            if port.isdigit():
                port_num = int(port)
                
                # Check if it's a list selection (1, 2, 3, 4)
                if port_num <= len(available_ports) and port_num >= 1:
                    # User selected from the list (1-indexed)
                    port = available_ports[port_num - 1]['port']
                    print(f"Selected from list: {port}")
                else:
                    # User entered a COM port number directly (e.g., "4" means "COM4")
                    port = f"COM{port_num}"
                    print(f"Interpreted as: {port}")
            
            # If user entered something like "com4" or "COM4", normalize it
            elif port.upper().startswith("COM"):
                port = port.upper()
        else:
            # Auto-detect port
            if not available_ports:
                print("No Bluetooth COM ports found!")
                print("\nTo set up Bluetooth:")
                print("1. Pair your phone with this PC")
                print("2. On your phone, open Bluetooth Terminal app")
                print("3. Connect to this PC")
                print("4. A COM port will be created automatically")
                return False
            
            # Use first available port
            port = available_ports[0]['port']
            print(f"Auto-selected port: {port} ({available_ports[0]['description']})")
        
        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=baud_rate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            
            self.running = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            
            print(f"\n✓ Bluetooth server started on {port}")
            print(f"  Baud rate: {baud_rate}")
            print("\nTo connect from your phone:")
            print("1. Download 'Serial Bluetooth Terminal' app (Android)")
            print("   or 'Bluetooth Terminal' app (iOS)")
            print("2. Pair your phone with this PC if not already paired")
            print("3. In the app, select this PC from paired devices")
            print("4. Start chatting with NOVA!\n")
            
            # Send welcome message
            self._send_response("NOVA Bluetooth Connected! Type /help for commands.\n")
            
            return True
            
        except serial.SerialException as e:
            print(f"Error opening port {port}: {e}")
            print("\nMake sure:")
            print("1. Your phone is paired with this PC")
            print("2. You've connected via Bluetooth Terminal app on your phone")
            print("3. The correct COM port is selected")
            return False
        except Exception as e:
            print(f"Error: {e}")
            return False
    
    def stop(self):
        """Stop the Bluetooth server."""
        self.running = False
        
        if self.serial_port and self.serial_port.is_open:
            try:
                self._send_response("NOVA Bluetooth disconnected. Goodbye!\n")
                self.serial_port.close()
            except:
                pass
        
        self.serial_port = None
        print("Bluetooth server stopped")
    
    def _listen_loop(self):
        """Main loop to listen for incoming messages."""
        buffer = ""
        
        while self.running and self.serial_port and self.serial_port.is_open:
            try:
                if self.serial_port.in_waiting > 0:
                    # Read available data
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    try:
                        text = data.decode('utf-8', errors='ignore')
                    except:
                        text = data.decode('latin-1', errors='ignore')
                    
                    buffer += text
                    
                    # Process complete lines
                    while '\n' in buffer or '\r' in buffer:
                        # Split on newline or carriage return
                        for sep in ['\r\n', '\n', '\r']:
                            if sep in buffer:
                                line, buffer = buffer.split(sep, 1)
                                break
                        
                        line = line.strip()
                        if line:
                            self._handle_message(line)
                
                time.sleep(0.1)  # Small delay to prevent CPU overuse
                
            except serial.SerialException as e:
                print(f"Bluetooth connection error: {e}")
                self.running = False
                break
            except Exception as e:
                print(f"Error in Bluetooth loop: {e}")
                time.sleep(1)
    
    def _handle_message(self, message: str):
        """Handle incoming message from phone."""
        print(f"[BT] Received: {message}")
        
        # Handle built-in commands
        if message.lower() in ['/help', 'help', '?']:
            help_text = """
=== NOVA Bluetooth Commands ===
/status  - System status
/apps    - Running apps
/lock    - Lock screen
/open X  - Open app X
/close X - Close app X
/cmd X   - Run command X
/exit    - Disconnect

Or just chat with NOVA!
===============================
"""
            self._send_response(help_text)
            return
        
        elif message.lower() == '/status':
            try:
                import psutil
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory().percent
                battery = psutil.sensors_battery()
                bat_pct = battery.percent if battery else "N/A"
                
                status = f"""
System Status:
  CPU: {cpu}%
  Memory: {mem}%
  Battery: {bat_pct}%
"""
                self._send_response(status)
            except:
                self._send_response("Error getting system status\n")
            return
        
        elif message.lower() == '/lock':
            try:
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                self._send_response("Screen locked!\n")
            except:
                self._send_response("Error locking screen\n")
            return
        
        elif message.lower().startswith('/open '):
            app = message[6:].strip()
            try:
                subprocess.Popen(f'start "" "{app}"', shell=True)
                self._send_response(f"Opening {app}...\n")
            except Exception as e:
                self._send_response(f"Error: {e}\n")
            return
        
        elif message.lower().startswith('/close '):
            app = message[7:].strip()
            try:
                subprocess.run(f'taskkill /IM "{app}.exe" /F', shell=True, capture_output=True)
                self._send_response(f"Closed {app}\n")
            except Exception as e:
                self._send_response(f"Error: {e}\n")
            return
        
        elif message.lower().startswith('/cmd '):
            cmd = message[5:].strip()
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
                output = result.stdout or result.stderr or "Command executed"
                self._send_response(f"{output[:500]}\n")
            except Exception as e:
                self._send_response(f"Error: {e}\n")
            return
        
        elif message.lower() in ['/exit', '/quit', '/bye']:
            self._send_response("Goodbye! Disconnecting...\n")
            self.stop()
            return
        
        # Pass to NOVA AI if available
        if self.nova:
            try:
                response = self.nova.process(message)
                self._send_response(f"\n{response}\n\n")
            except Exception as e:
                self._send_response(f"NOVA Error: {e}\n")
        else:
            # Echo mode if NOVA not connected
            self._send_response(f"Echo: {message}\n")
    
    def _send_response(self, text: str):
        """Send response back to the phone."""
        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(text.encode('utf-8'))
                self.serial_port.flush()
            except Exception as e:
                print(f"Error sending response: {e}")


def list_com_ports():
    """List all available COM ports."""
    if not SERIAL_AVAILABLE:
        print("pyserial not installed. Run: pip install pyserial")
        return
    
    ports = serial.tools.list_ports.comports()
    
    if not ports:
        print("No COM ports found!")
        print("\nTo create a Bluetooth COM port:")
        print("1. Open Windows Settings > Devices > Bluetooth")
        print("2. Pair your phone with this PC")
        print("3. On your phone, use a Bluetooth Terminal app")
        print("4. Connect to this PC - a COM port will be created")
        return
    
    print("\n=== Available COM Ports ===")
    for i, port in enumerate(ports, 1):
        bt_marker = " [Bluetooth?]" if any(k in port.description.lower() for k in ['bluetooth', 'spp', 'bth']) else ""
        print(f"{i}. {port.device}: {port.description}{bt_marker}")
    print()


def main():
    """Test the Bluetooth server standalone."""
    import argparse
    
    parser = argparse.ArgumentParser(description="NOVA Bluetooth Server")
    parser.add_argument("--port", "-p", help="COM port (e.g., COM5)")
    parser.add_argument("--baud", "-b", type=int, default=9600, help="Baud rate")
    parser.add_argument("--list", "-l", action="store_true", help="List COM ports")
    args = parser.parse_args()
    
    if args.list:
        list_com_ports()
        return
    
    print("=" * 50)
    print("       NOVA Bluetooth Server")
    print("=" * 50)
    
    list_com_ports()
    
    server = BluetoothServer()
    
    if args.port:
        server.start(port=args.port, baud_rate=args.baud)
    else:
        # Interactive mode
        port = input("Enter COM port (e.g., COM5) or press Enter for auto: ").strip()
        if port:
            server.start(port=port, baud_rate=args.baud)
        else:
            server.start(baud_rate=args.baud)
    
    if server.running:
        print("\nBluetooth server running. Press Ctrl+C to stop.")
        try:
            while server.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping...")
            server.stop()


if __name__ == "__main__":
    main()
