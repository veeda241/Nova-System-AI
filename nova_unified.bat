@echo off
setlocal
cd /d "%~dp0"
echo Launching Nova Unified (CLI + Graphical HUD)...
python -B nova_cli.py --gui
pause
