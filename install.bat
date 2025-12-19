@echo off
:: NOVA Installer - Adds NOVA to your system PATH
:: Run this as Administrator!

echo.
echo  ███╗   ██╗ ██████╗ ██╗   ██╗ █████╗
echo  ████╗  ██║██╔═══██╗██║   ██║██╔══██╗
echo  ██╔██╗ ██║██║   ██║██║   ██║███████║
echo  ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║
echo  ██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║
echo  ╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝
echo.
echo  Installing NOVA to system PATH...
echo.

:: Get the directory where this script is located
set "NOVA_PATH=%~dp0"
set "NOVA_PATH=%NOVA_PATH:~0,-1%"

:: Add to User PATH (doesn't need admin)
echo Adding %NOVA_PATH% to PATH...

:: Use PowerShell to add to user PATH permanently
powershell -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';%NOVA_PATH%', 'User')"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo  [OK] NOVA installed successfully!
    echo.
    echo  Close this terminal and open a new one.
    echo  Then type: nova
    echo.
) else (
    echo.
    echo  [X] Installation failed. Try running as Administrator.
    echo.
)

pause
