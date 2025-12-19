# NOVA - AI Coding Assistant
# Run from anywhere by typing: nova

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path

# Check if Ollama is running
if (-not (Get-Process -Name "ollama" -ErrorAction SilentlyContinue)) {
    Write-Host "Starting Ollama server..." -ForegroundColor Cyan
    try {
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden -ErrorAction Stop
        # Wait for it to initialize
        Start-Sleep -Seconds 5
    } catch {
        Write-Host "Warning: Could not start Ollama automatically. You may need to run 'ollama serve' manually." -ForegroundColor Yellow
    }
}

python "$ScriptPath\nova_cli.py" @args