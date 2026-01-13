@echo off
title NOVA Enhanced MCP Agent
cd /d "%~dp0"
python agent\enhanced_agent.py %*
pause
