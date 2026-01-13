@echo off
chcp 65001 >nul 2>&1
python -B "%~dp0Core Files\nova_cli.py" %*
