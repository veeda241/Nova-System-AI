# NOVA - AI Coding Assistant
# Run from anywhere by typing: nova

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# Check if Ollama is running
if (-not (Get-Process -Name "ollama" -ErrorAction SilentlyContinue)) {
    Write-Host "Starting Ollama server..." -ForegroundColor Cyan
    try {
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -ErrorAction Stop
        Start-Sleep -Seconds 3
    } catch {
        Write-Host "Warning: Could not start Ollama automatically." -ForegroundColor Yellow
    }
}

python "$ScriptPath\interface\cli.py" @args
