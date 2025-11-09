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
