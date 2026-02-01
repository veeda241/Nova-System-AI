@echo off
title NOVA Model Builder
cd /d "%~dp0\.."

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║           NOVA Custom Model Builder for Ollama                ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.

echo [1/3] Checking Ollama status...
ollama list >nul 2>&1
if errorlevel 1 (
    echo ❌ Ollama is not running. Please start Ollama first.
    echo    Run: ollama serve
    pause
    exit /b 1
)
echo ✅ Ollama is running

echo.
echo [2/3] Building NOVA custom model...
echo     Base: qwen2.5-coder
echo     Features: MCP tool execution
echo.

ollama create nova -f Config\Modelfile.nova

if errorlevel 1 (
    echo ❌ Failed to create model
    pause
    exit /b 1
)

echo.
echo [3/3] Verifying model...
ollama list | findstr "nova"

echo.
echo ╔═══════════════════════════════════════════════════════════════╗
echo ║  ✅ NOVA model created successfully!                          ║
echo ║                                                                ║
echo ║  Usage:                                                        ║
echo ║    ollama run nova                                             ║
echo ║    python -m agent.claude_mcp_agent  (with model=nova)        ║
echo ╚═══════════════════════════════════════════════════════════════╝
echo.
pause
