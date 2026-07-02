@echo off
title NOVA Claude MCP Agent
cd /d "%~dp0\.."
python -m agent.claude_mcp_agent %*
pause
