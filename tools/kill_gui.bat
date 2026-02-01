@echo off
echo Killing Nova GUI...

:: Method 1: PowerShell (Precise)
powershell -Command "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*gui.py*' } | ForEach-Object { echo 'Killing PID ' + $_.ProcessId; Stop-Process -Id $_.ProcessId -Force }"

:: Method 2: WMIC (Fallback)
wmic process where "CommandLine like '%gui.py%'" call terminate

echo Done.
