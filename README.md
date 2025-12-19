<<<<<<< HEAD
# NOVA - Your Desktop AI Assistant

## About NOVA

NOVA is a desktop assistant that helps you control your Windows system with natural language commands. Built with Python and powered by a local AI model, NOVA provides a simple chat interface to perform a variety of system tasks, from opening applications to analyzing system performance. It's designed to be a helpful and extensible tool for automating your daily workflows.

## Features

NOVA can understand and execute a wide range of commands, including:

📂 **File and Application Management**
- `open application [app_name_or_path]`: Launch any application, document, or folder.
- `open multiple applications [app1, app2, ...]`: Launch several applications at once.
- `close application [process_name.exe]`: Terminate a running application.
- `delete file [full_file_path]`: Delete a file from your system (use with caution).

⚙️ **System & Process Automation**
- `run command [shell_command]`: Execute any shell command directly for advanced tasks.
- `list processes`: Get a list of all currently running processes.

🧠 **System Interaction and Monitoring**
- `system analysis`: Check current CPU, memory, and battery status.
- `disk usage`: Display usage statistics for all disk drives.
- `clean temp files`: Clear out your system's temporary files folder.

## How to Install and Run (from GitHub)

Follow these steps to set up NOVA on a new device.

### Prerequisites
- [Python 3](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads/)

### Installation Steps

1.  **Clone the repository:**
    Open a command prompt or terminal and clone the project from GitHub.
    ```bash
    git clone https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
    ```

2.  **Navigate to the project directory:**
    ```bash
    cd Nova-System-AI
    ```

3.  **Install required packages:**
    Install all the necessary Python libraries using the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

### Running NOVA

To launch the application, simply run the `nova.bat` file:
```bash
nova.bat
```
This will open the NOVA chat window, and you can start giving it commands!

## How to Use

Just type your command into the input box and press Enter. For example:
- `open application chrome`
- `system analysis`
- `help` (to see the full list of commands)
=======
# NOVA

**Advanced AI Coding Assistant**

```
                      ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗
                      ████╗  ██║██╔═══██╗██║   ██║██╔══██╗
                      ██╔██╗ ██║██║   ██║██║   ██║███████║
                      ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║
                      ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║
                      ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝

                           Advanced AI Coding Assistant v1.0
```

## Quick Start with Ollama (Recommended)

### 1. Install Ollama
Download from: https://ollama.ai

### 2. Pull a model
```powershell
ollama pull llama3.2
```

### 3. Run NOVA
```powershell
python nova_cli.py
```

That's it! NOVA will auto-detect Ollama and use it.

## Features

### 🤖 System Control
- **System Status** — CPU, Memory, Battery, Uptime
- **Open/Close Apps** — "Open Chrome", "Close notepad"
- **Lock Screen** — Secure your laptop instantly
- **File Search** — Find files anywhere

### 📱 Phone Access
- Built-in web server for remote control
- Access from any device on your network
- Run `/web` to start

### 🔵 Bluetooth Access
- Connect your phone via Bluetooth
- Control NOVA using Bluetooth Terminal app
- Run `/bluetooth` to start

### 🤖 MCP Agent (Code Generation & Execution)
- Generate Python code from natural language prompts
- Automatically create and execute .py files
- Safe execution with security checks and timeout
- Run `/agent` to start

### 💻 AI Coding Assistant
- Read, write, and analyze code
- Execute Python and shell commands
- Works 100% offline with Ollama

## Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/status` | System status |
| `/model` | Change AI model |
| `/web` | Start web server for phone |
| `/bluetooth` | Start Bluetooth server for phone |
| `/agent` | Start MCP Agent (code generation) |
| `/clear` | Clear screen |
| `/exit` | Exit NOVA |

## Available Models (Ollama)

| # | Model | Install Command |
|---|-------|-----------------|
| 1 | Llama 3.2 | `ollama pull llama3.2` |
| 2 | CodeLlama | `ollama pull codellama` |
| 3 | Mistral | `ollama pull mistral` |
| 4 | DeepSeek Coder | `ollama pull deepseek-coder` |
| 5 | Qwen Coder | `ollama pull qwen2.5-coder` |

Switch models with `/model` command.

## 🔵 Bluetooth Setup Guide

### Step 1: Install Dependencies
```bash
pip install pyserial
```

### Step 2: Pair Your Phone
1. Open Windows **Settings > Bluetooth & devices**
2. Enable Bluetooth on your phone
3. Pair your phone with your PC

### Step 3: Download Bluetooth Terminal App
- **Android:** "Serial Bluetooth Terminal" (free on Play Store)
- **iOS:** "Bluetooth Terminal" or similar

### Step 4: Connect to NOVA
1. Run NOVA on your PC
2. Type `/bluetooth` in NOVA
3. Select the COM port when prompted
4. In your phone app, connect to your PC
5. Start chatting with NOVA!

### Bluetooth Commands (from phone)
| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/status` | System status |
| `/lock` | Lock screen |
| `/open X` | Open app X |
| `/close X` | Close app X |
| `/cmd X` | Run command X |

## Requirements

```
pip install rich psutil pyserial
```

Ollama handles the AI models - no other dependencies needed!


## License

MIT

---

**NOVA - Advanced AI Coding Assistant**  
*Made by Spiderboy*
>>>>>>> baaa0b2 (NOVA v1.1 - Ollama AI with tool execution)
