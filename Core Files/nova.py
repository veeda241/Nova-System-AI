import os
import random
import shutil
import tempfile
import psutil
import ollama
import tkinter as tk
from tkinter import scrolledtext
import threading
import subprocess
import win32api
import win32process
import win32con
import winshell  # Added for the new function
from tkinter import messagebox # Import messagebox for confirmation dialog

# --- Helper Functions for System Commands ---

def open_all_applications():
    """Finds and opens all applications from the Start Menu."""
    try:
        start_menu = winshell.start_menu()
        opened_count = 0
        error_count = 0
        app_list = []
        for root, dirs, files in os.walk(start_menu):
            for file in files:
                if file.endswith(".lnk"):
                    lnk_path = os.path.join(root, file)
                    try:
                        shortcut = winshell.shortcut(lnk_path)
                        target_path = shortcut.path
                        if target_path and os.path.exists(target_path):
                            app_list.append(target_path)
                    except Exception:
                        pass # Ignore broken shortcuts

        if not app_list:
            return "No applications found to open."

        # Ask for confirmation before opening a large number of apps
        if messagebox.askyesno("Confirmation", f"Found {len(app_list)} applications. Are you sure you want to open all of them?"):
            for target_path in app_list:
                try:
                    subprocess.Popen(f'"{target_path}"', shell=True)
                    opened_count += 1
                except Exception:
                    error_count += 1
            return f"Sir spiderboy: Attempted to open {opened_count} applications. Failed to open {error_count}."
        else:
            return "Sir spiderboy: Operation cancelled by user."
    except Exception as e:
        return f"Sir spiderboy: An error occurred while trying to open all applications: {e}"


def open_application(app_name_or_path):
    """Opens an application on Windows by searching for it in the Start Menu or using common aliases."""
    common_apps = {
        "notepad": "notepad.exe",
        "chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "cmd": "cmd.exe",
        "powershell": "powershell.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "settings": "ms-settings:",  # Special case for Windows Settings
    }

    target_app = app_name_or_path.lower()
    app_to_open = None

    # 1. Check common apps dictionary first
    if target_app in common_apps:
        app_to_open = common_apps[target_app]
    else:
        # 2. If not in common_apps, search the Start Menu for a matching shortcut
        try:
            start_menu = winshell.start_menu()
            found_path = None
            for root, dirs, files in os.walk(start_menu):
                for file in files:
                    if file.lower().endswith(".lnk"):
                        shortcut_name = os.path.splitext(file)[0].lower()
                        if target_app in shortcut_name:
                            lnk_path = os.path.join(root, file)
                            shortcut = winshell.shortcut(lnk_path)
                            if shortcut.path and os.path.exists(shortcut.path):
                                found_path = shortcut.path
                                break
                if found_path:
                    break
            
            if found_path:
                app_to_open = found_path
            elif "." not in target_app and not os.path.exists(target_app):
                app_to_open = target_app + ".exe"
            else:
                app_to_open = app_name_or_path
        except Exception:
            app_to_open = app_name_or_path

    print(f"Attempting to open: {app_to_open}")
    try:
        if app_to_open and app_to_open.startswith("ms-settings:"):
            subprocess.Popen(['start', app_to_open], shell=True)
        elif app_to_open and app_to_open.startswith("shell:AppsFolder"):
            subprocess.Popen(['explorer.exe', app_to_open])
        else:
            win32api.ShellExecute(0, "open", app_to_open, None, None, win32con.SW_SHOWNORMAL)
        return f"Sir spiderboy: Successfully attempted to open '{app_name_or_path}'. Check your desktop or taskbar."
    except (win32api.error, OSError) as e:
        error_message = getattr(e, 'strerror', str(e))
        return f"Sir spiderboy: Error opening '{app_name_or_path}': {error_message}. Please ensure the application name or path is correct and accessible."
    except Exception as e:
        return f"Sir spiderboy: An unexpected error occurred while trying to open '{app_name_or_path}': {e}. Please ensure the application name or path is correct."

def close_application(app_name):
    """Closes an application by its process image name on Windows using pywin32."""
    app_name_lower = app_name.lower()
    closed_count = 0
    for pid in win32process.EnumProcesses():
        try:
            handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE | win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid)
            if handle:
                try:
                    # Get the full path of the executable
                    exe_path = win32process.GetModuleFileNameEx(handle, 0)
                    # Extract just the executable name
                    exe_name = os.path.basename(exe_path).lower()

                    if exe_name == app_name_lower:
                        win32api.TerminateProcess(handle, 0)
                        win32api.CloseHandle(handle)
                        closed_count += 1
                except Exception as e_inner:
                    # Handle cases where GetModuleFileNameEx might fail (e.g., system processes)
                    pass
                finally:
                    win32api.CloseHandle(handle)
        except Exception as e_outer:
            # Handle cases where OpenProcess might fail (e.g., access denied)
            pass
    
    if closed_count > 0:
        return f"Sir spiderboy: Successfully closed {closed_count} instance(s) of '{app_name}'. (Requires exact process image name, e.g., 'chrome.exe')"
    else:
        return f"Sir spiderboy: Could not find or close any instance of '{app_name}'. Please ensure you provide the exact process image name (e.g., 'chrome.exe')."

def delete_file_at_path(file_path):
    """Deletes a file at the specified absolute path."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return f"Sir spiderboy: Successfully deleted '{file_path}'."
        else:
            return f"Sir spiderboy: File not found at '{file_path}'."
    except Exception as e:
        return f"Sir spiderboy: Error deleting '{file_path}': {e}"

def get_system_performance():
    """Gets system performance metrics, with improved reliability."""
    try:
        # Calling cpu_percent once with a small interval gives a more reliable reading
        psutil.cpu_percent(interval=0.1)
        cpu_percent = psutil.cpu_percent()
        
        memory_info = psutil.virtual_memory()
        battery = psutil.sensors_battery()
        disk_info = psutil.disk_usage('C:\\') # Get disk usage for C: drive
        
        performance_stats = f"CPU Usage: {cpu_percent}%\n"
        performance_stats += f"Memory Usage: {memory_info.percent}%\n"
        performance_stats += f"Disk C: Usage: {disk_info.percent}% (Total: {disk_info.total / (1024**3):.2f} GB, Used: {disk_info.used / (1024**3):.2f} GB, Free: {disk_info.free / (1024**3):.2f} GB)\n"
        
        if battery:
            performance_stats += f"Battery Level: {battery.percent}%"
            if battery.power_plugged:
                performance_stats += " (Charging)"
            else:
                performance_stats += " (Not Charging)"
        else:
            performance_stats += "Battery information not available."
            
        return f"Sir spiderboy: {performance_stats}"
    except Exception as e:
        return f"Sir spiderboy: An error occurred while fetching system performance: {e}"

def clean_temp_files():
    """Cleans the system's temporary files."""
    temp_dir = tempfile.gettempdir()
    cleaned_files = 0
    errors = 0
    for item in os.listdir(temp_dir):
        item_path = os.path.join(temp_dir, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
                cleaned_files += 1
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                cleaned_files += 1
        except Exception as e:
            errors += 1
    return f"Sir spiderboy: Cleaned {cleaned_files} items from the temporary directory. Could not clean {errors} items."

def list_processes():
    """Lists all running processes on Windows."""
    try:
        result = subprocess.run(["tasklist"], check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        return f"Sir spiderboy: {result.stdout}"
    except subprocess.CalledProcessError as e:
        return f"Sir spiderboy: Error listing processes: {e.stderr.strip()}"
    except Exception as e:
        return f"Sir spiderboy: An unexpected error occurred while trying to list processes: {e}"

def get_disk_usage():
    """Gets information about disk partitions and their usage."""
    disk_info = "Disk Usage:\n"
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_info += f"  Drive: {partition.device} ({partition.mountpoint})\n"
            disk_info += f"    Total: {usage.total / (1024**3):.2f} GB\n"
            disk_info += f"    Used: {usage.used / (1024**3):.2f} GB ({usage.percent}%)\n"
            disk_info += f"    Free: {usage.free / (1024**3):.2f} GB\n"
        except Exception as e:
            disk_info += f"  Drive: {partition.device} ({partition.mountpoint}) - Error accessing: {e}\n"
    return disk_info

def launch_multiple_applications(app_names_str):
    """Launches multiple applications sequentially."""
    app_names = [app.strip() for app in app_names_str.split(',') if app.strip()]
    results = []
    for app_name in app_names:
        result = open_application(app_name)
        results.append(result)
    return "\n".join(results)

def execute_shell_command(command):
    """Executes a shell command and returns its output."""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        return f"Sir spiderboy: Command executed successfully.\nStdout:\n{result.stdout}\nStderr:\n{result.stderr}"
    except subprocess.CalledProcessError as e:
        return f"Sir spiderboy: Error executing command.\nStderr:\n{e.stderr}\nStdout:\n{e.stdout}"
    except Exception as e:
        return f"Sir spiderboy: An unexpected error occurred: {e}"

def get_help_message():
    """Returns a help message for NOVA's commands."""
    help_msg = "Sir spiderboy: NOVA Commands:\n"
    help_msg += "  - 'open application [app_name_or_path]': Opens an application. You can use common names (e.g., 'notepad', 'chrome', 'settings', 'file explorer'), the full path to the executable, or a UWP app identifier (e.g., 'shell:AppsFolder\\Microsoft.WindowsCalculator_8wekyb3d8bbwe!App').\n"
    help_msg += "  - 'open all apps': Finds and opens all applications from your Start Menu.\n"
    help_msg += "  - 'close application [process_image_name]': Closes an application. IMPORTANT: Use 'list processes' first to find the EXACT process image name (e.g., 'chrome.exe', 'notepad.exe').\n"
    help_msg += "  - 'delete file [full_file_path]': Deletes a file. Requires the full, absolute path. Use with caution!\n"
    help_msg += "  - 'system analysis': Shows current CPU, memory, battery, and disk usage.\n"
    help_msg += "  - 'clean temp files': Cleans temporary files from your system.\n"
    help_msg += "  - 'list processes': Lists all running processes to help identify application names for closing.\n"
    help_msg += "  - 'disk usage': Shows information about disk partitions and their usage.\n"
    help_msg += "  - 'open multiple applications [app1, app2, ...]': Opens several applications sequentially. Provide a comma-separated list of app names or paths.\n"
    help_msg += "  - 'run command [your_shell_command]': Executes any shell command. USE WITH EXTREME CAUTION! This gives NOVA full control over your system. You will be asked for confirmation.\n"
    help_msg += "  - 'help': Displays this help message.\n"
    help_msg += "For general chat, just type your message!"
    return help_msg

# --- Chatbot GUI Class ---

class ChatbotGUI:
    def __init__(self, master):
        self.master = master
        master.title("NOVA")
        master.configure(bg="black")

        self.chat_history = scrolledtext.ScrolledText(master, wrap=tk.WORD, bg="black", fg="lightgreen", font=("Courier New", 10))
        self.chat_history.pack(padx=10, pady=2, fill=tk.BOTH, expand=True) # Adjusted pady, added fill/expand
        self.chat_history.tag_configure("thinking_tag", foreground="gray") # Configure tag for thinking message

        self.input_field = tk.Text(master, width=50, height=3, bg="black", fg="lightgreen", font=("Courier New", 10), insertbackground="lightgreen", highlightthickness=0, borderwidth=1, relief="solid")
        self.input_field.pack(padx=10, pady=2, fill=tk.X) # Adjusted pady, added fill
        self.input_field.bind("<Return>", self.send_message)
        self.input_field.bind("<Shift-Return>", self.insert_newline)

        self.chat_history.insert(tk.END, "NOVA: Hello, Sir spiderboy! I'm NOVA, an AI built by spiderboy using the gemma llm model.\n")
        self.thinking_message_tag = "thinking_tag" # Store the tag name
        self.input_field.focus_set() # Set focus to input field

    def insert_newline(self, event=None):
        self.input_field.insert(tk.INSERT, "\n")
        return "break"

    def get_ollama_response_threaded(self, user_input, chat_history, master, thinking_message_tag, input_field):
        try:
            ollama_response = ollama.chat(
                model='gemma3:4b',
                messages=[
                    {'role': 'system', 'content': 'You are NOVA, an AI assistant built by spiderboy.'},
                    {'role': 'user', 'content': user_input}
                ]
            )
            response_text = ollama_response['message']['content']
            
            def update_gui():
                chat_history.tag_remove(thinking_message_tag, "1.0", tk.END) # Remove thinking message by tag
                chat_history.insert(tk.END, f"NOVA: {response_text}\n")
                input_field.config(state=tk.NORMAL)
                chat_history.see(tk.END)

            master.after(0, update_gui)

        except Exception as e:
            def handle_error():
                chat_history.tag_remove(thinking_message_tag, "1.0", tk.END) # Remove thinking message by tag
                chat_history.insert(tk.END, f"NOVA: Error communicating with Ollama: {e}\n")
                input_field.config(state=tk.NORMAL)
                chat_history.see(tk.END)
            master.after(0, handle_error)

    def send_message(self, event=None):
        user_input = self.input_field.get("1.0", tk.END).strip()
        self.input_field.delete("1.0", tk.END)

        if not user_input.strip():
            return

        # Insert user's message
        self.chat_history.insert(tk.END, f"You: {user_input}\n")
        self.chat_history.see(tk.END)

        response_to_display = None

        if user_input.lower() == "open all apps":
            response_to_display = open_all_applications()
        elif user_input.lower().startswith("open application "):
            app_name = user_input[len("open application "):].strip()
            response_to_display = open_application(app_name)
        elif user_input.lower().startswith("open "):
            app_name = user_input[len("open "):].strip()
            response_to_display = open_application(app_name)
        elif user_input.lower().startswith("close application "):
            app_name = user_input[len("close application "):].strip()
            response_to_display = close_application(app_name)
        elif user_input.lower().startswith("delete file "):
            file_path = user_input[len("delete file "):].strip()
            response_to_display = delete_file_at_path(file_path)
        elif "system analysis" in user_input.lower():
            response_to_display = get_system_performance()
        elif "clean temp files" in user_input.lower():
            response_to_display = clean_temp_files()
        elif "list processes" in user_input.lower():
            response_to_display = list_processes()
        elif "disk usage" in user_input.lower():
            response_to_display = get_disk_usage()
        elif user_input.lower().startswith("open multiple applications "):
            app_names_str = user_input[len("open multiple applications "):].strip()
            response_to_display = launch_multiple_applications(app_names_str)
        elif user_input.lower().startswith("run command "):
            command_to_execute = user_input[len("run command "):].strip()
            if messagebox.askyesno("Confirmation", f"WARNING: You are about to execute the command:\n\n'{command_to_execute}'\n\nThis gives NOVA full control over your system. Are you sure you want to proceed?"):
                response_to_display = execute_shell_command(command_to_execute)
            else:
                response_to_display = "Command execution cancelled by user."
        elif "help" in user_input.lower():
            response_to_display = get_help_message()
        
        if response_to_display:
            self.chat_history.insert(tk.END, f"NOVA: {response_to_display}\n")
            self.chat_history.see(tk.END)
        else:
            self.chat_history.insert(tk.END, "NOVA: Thinking...\n", self.thinking_message_tag) # Insert with tag
            self.chat_history.see(tk.END)
            self.input_field.config(state=tk.DISABLED)
            threading.Thread(target=self.get_ollama_response_threaded, args=(user_input, self.chat_history, self.master, self.thinking_message_tag, self.input_field)).start()
        
        return "break"

def main():
    """Main function for the NOVA assistant."""
    root = tk.Tk()
    chatbot_gui = ChatbotGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()