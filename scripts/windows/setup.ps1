# Open Media Center - one-time setup for Windows 10/11 (Windows PowerShell 5.1 or PowerShell 7).
# Creates backend\.venv and installs the pinned Python packages. Uses vendor\wheels (offline) when present.
# Builds the web UI only if frontend\dist is missing or -BuildUI is given (needs Node.js 20.19+).
# No administrator rights, Docker, accounts or cloud services are needed.
param([switch]$BuildUI, [switch]$Online)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$Wheels = Join-Path $Root "vendor\wheels"

function Step($msg) { Write-Host "`n== $msg" -ForegroundColor Yellow }

Step "Checking Python"
$PyExe = $null; $PyArgs = @()
foreach ($candidate in @(@("py", "-3"), @("python"))) {
    $cmd = Get-Command $candidate[0] -ErrorAction SilentlyContinue
    if ($cmd) {
        $args2 = @($candidate | Select-Object -Skip 1)
        & $candidate[0] @args2 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
        if ($LASTEXITCODE -eq 0) { $PyExe = $candidate[0]; $PyArgs = $args2; break }
    }
}
if (-not $PyExe) {
    throw "Python 3.11+ not found. Install it from https://www.python.org/downloads/windows/ (tick 'Add python.exe to PATH'), then rerun Setup.bat. Note: the Microsoft Store 'python' alias opens the Store instead - disable it under Settings > Apps > Advanced app settings > App execution aliases."
}
& $PyExe @PyArgs -c "import sys, platform; print('Python', sys.version.split()[0], platform.machine())"

Step "Creating virtual environment (backend\.venv)"
$Venv = Join-Path $Backend ".venv"
$VenvPy = Join-Path $Venv "Scripts\python.exe"
if (-not (Test-Path $VenvPy)) { & $PyExe @PyArgs -m venv $Venv }
if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }

Step "Installing Python packages"
$req = Join-Path $Backend "requirements-dev.txt"
if ((Test-Path $Wheels) -and -not $Online) {
    Write-Host "Using bundled wheels (offline): $Wheels"
    & $VenvPy -m pip install --no-index --find-links $Wheels -r $req
} else {
    Write-Host "Downloading from PyPI (internet needed once)."
    & $VenvPy -m pip install -r $req
}
if ($LASTEXITCODE -ne 0) { throw "Package installation failed. If offline, your Python version may have no bundled wheel (bundled: CPython 3.11-3.14, 64-bit). Re-run with internet: Setup.bat -Online" }

$Dist = Join-Path $Frontend "dist\index.html"
if ($BuildUI -or -not (Test-Path $Dist)) {
    Step "Building the web UI"
    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $node) { throw "frontend\dist is missing and Node.js 20.19+ is not installed. Install Node.js LTS, or use the release zip which contains frontend\dist." }
    Push-Location $Frontend
    try {
        corepack enable
        yarn install --frozen-lockfile
        yarn build
        if ($LASTEXITCODE -ne 0) { throw "UI build failed." }
    } finally { Pop-Location }
}

Step "Running startup checks"
& $VenvPy (Join-Path $Backend "run.py") --check
if ($LASTEXITCODE -ne 0) { Write-Host "Some checks failed (see above)." -ForegroundColor Red; exit 1 }

Write-Host "`nSetup complete. Double-click Start.bat to run Open Media Center." -ForegroundColor Green
