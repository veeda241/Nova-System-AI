# Fast health sweep: unit tests, then the CLI commands that must work with no engine
# and no API key. Run: .\scripts\smoke.ps1
param([switch]$SkipTests, [switch]$Quick)

$ErrorActionPreference = "Continue"   # native stderr must not abort a check

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Src = Join-Path $RepoRoot "src"
Set-Location $RepoRoot

# Use the repo directly when the package is not pip-installed.
& python -B -c "import importlib.util,sys;sys.exit(0 if importlib.util.find_spec('nova') else 1)" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { $env:PYTHONPATH = "$Src" }
$env:PYTHONWARNINGS = "ignore"

$script:failures = @()

function Check([string]$Label, [scriptblock]$Body, [int[]]$Okay = @(0)) {
    & $Body 2>&1 | ForEach-Object { Write-Host "  $_" }
    $code = $LASTEXITCODE
    if ($Okay -contains $code) {
        Write-Host ("PASS {0} (exit {1})" -f $Label, $code) -ForegroundColor Green
    } else {
        Write-Host ("FAIL {0} (exit {1})" -f $Label, $code) -ForegroundColor Red
        $script:failures += $Label
    }
}

Write-Host "`n== gate must refuse without approval ==" -ForegroundColor Cyan
Check "sandbox escape refused at yolo" {
    python -B -m nova tools call read_file path=../../Windows/win.ini --mode yolo
} @(1)
Check "catastrophic command hard blocked" {
    python -B -m nova tools call run_command "command=rm -rf /" --mode yolo
} @(1)
Check "write without approval is denied on a pipe" {
    "" | python -B -m nova tools call write_file path=smoke.txt content=denied
} @(1)

Write-Host "`n== CLI surface (no engine required) ==" -ForegroundColor Cyan
Check "nova --version" { python -B -m nova --version }
Check "nova doctor" { python -B -m nova doctor } @(0, 3)
Check "nova tools list" { python -B -m nova tools list }
Check "nova engine list" { python -B -m nova engine list }
Check "nova skills list" { python -B -m nova skills list }
Check "nova traces stats" { python -B -m nova traces stats }
Check "nova config paths --json" { python -B -m nova config paths --json }
Check "nova validate src/nova/config.py" { python -B -m nova validate src/nova/config.py }
Check "nova skills run workspace_audit --yolo" { python -B -m nova skills run workspace_audit --yolo }

if (-not $Quick) {
    Write-Host "`n== pytest ==" -ForegroundColor Cyan
    Check "pytest" { python -B -m pytest }
}

if ($script:failures) {
    Write-Host ("`n{0} check(s) failed: {1}" -f $script:failures.Count, ($script:failures -join ", ")) -ForegroundColor Red
    exit 1
}
Write-Host "`nall checks passed" -ForegroundColor Green
