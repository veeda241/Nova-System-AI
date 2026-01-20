@echo off
chcp 65001 >nul 2>&1
python -B "%~dp0nova_cli.py" %*
