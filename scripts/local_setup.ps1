# One-command local setup: start Ollama, pull a model, point Nova at it, verify.
# Run from PowerShell: .\scripts\local_setup.ps1
# Smaller model:         .\scripts\local_setup.ps1 -Model llama3.2:1b
# Server already up and model already pulled:  .\scripts\local_setup.ps1 -SkipPull
param(
    [string]$Model = "llama3.2",
    [switch]$SkipPull
)

$ErrorActionPreference = "Continue"   # native stderr must not abort the run

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Src = Join-Path $RepoRoot "src"
Set-Location $RepoRoot

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Ollama is not on PATH." -ForegroundColor Red
    Write-Host "Install it first:  winget install Ollama.Ollama"
    Write-Host "Then re-run this script."
    exit 1
}

& python -B -c "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('nova') else 1)" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    $env:PYTHONPATH = "$Src"
    Write-Host "nova is not pip-installed - using PYTHONPATH=$Src" -ForegroundColor Yellow
}
$env:PYTHONWARNINGS = "ignore"

function Invoke-Nova([string[]]$Arguments) {
    & python -B -m nova @Arguments 2>&1 | ForEach-Object { Write-Host "  $_" }
}

Write-Host "`n[1/4] Ollama server" -ForegroundColor Cyan
$tags = $null
try { $tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 } catch { $tags = $null }

if (-not $tags) {
    Write-Host "  not reachable - starting 'ollama serve' in a hidden window"
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    for ($i = 0; $i -lt 20; $i = $i + 1) {
        Start-Sleep -Seconds 2
        try { $tags = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3; break } catch { }
    }
    if (-not $tags) {
        Write-Host "  Ollama still is not answering on localhost:11434 - run 'ollama serve' yourself and retry." -ForegroundColor Red
        exit 1
    }
}
Write-Host "  online" -ForegroundColor Green

Write-Host "`n[2/4] model '$Model'" -ForegroundColor Cyan
$have = @()
if ($tags.models) { $have = @($tags.models | ForEach-Object { $_.name }) }
$match = @($have | Where-Object { $_ -like "$Model*" })

if ($match.Count -gt 0) {
    Write-Host "  already present: $($match[0])"
} elseif ($SkipPull) {
    Write-Host "  not pulled and -SkipPull was given. Installed models:" -ForegroundColor Yellow
    if ($have.Count) { $have | ForEach-Object { Write-Host "    $_" } } else { Write-Host "    (none)" }
    exit 1
} else {
    $answer = Read-Host "  pull '$Model' now? Roughly 2 GB download [y/N]"
    if ($answer -notmatch "^[yY]") {
        Write-Host "  skipped - try a smaller model: .\scripts\local_setup.ps1 -Model llama3.2:1b"
        exit 1
    }
    & ollama pull $Model
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  'ollama pull' failed (exit $LASTEXITCODE) - check disk space and connection." -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n[3/4] Nova settings" -ForegroundColor Cyan
Invoke-Nova @("config", "set", "engine", "ollama") | Out-Null
Invoke-Nova @("config", "set", "ollama_model", $Model) | Out-Null
Write-Host "  engine -> ollama | ollama_model -> $Model" -ForegroundColor Green
Write-Host "  cloud engines stay in the failover list; if you want local-only, remove the"
Write-Host "  GEMINI_API_KEY / GROQ_API_KEY from your environment or .env."

Write-Host "`n[4/4] verify" -ForegroundColor Cyan
Invoke-Nova @("engine", "list")
Invoke-Nova @("ask", "Reply with exactly: nova local online")
Write-Host "`nIf the answer is tagged (ollama) the whole loop runs on your machine." -ForegroundColor Cyan
