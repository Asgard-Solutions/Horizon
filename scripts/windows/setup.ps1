# Open Media Center - Phase 0 setup for Windows 10/11 (PowerShell 5+).
# Creates a local Python virtual environment and (optionally) builds the web UI. No admin rights needed.
param([switch]$BuildUI)
$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"

Write-Host "== Open Media Center setup ==" -ForegroundColor Yellow
$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) { $PyExe = "py"; $PyArgs = @("-3") } else { $PyExe = "python"; $PyArgs = @() }
& $PyExe @PyArgs -c "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ required'; print('Python', sys.version.split()[0])"
if ($LASTEXITCODE -ne 0) { throw "Python 3.11 or newer is required (https://www.python.org/downloads/windows/)." }

$Venv = Join-Path $Backend ".venv"
if (-not (Test-Path $Venv)) { & $PyExe @PyArgs -m venv $Venv }
$VenvPy = Join-Path $Venv "Scripts\python.exe"
& $VenvPy -m pip install --upgrade pip
& $VenvPy -m pip install -r (Join-Path $Backend "requirements-dev.txt")

$Dist = Join-Path $Frontend "dist\index.html"
if ($BuildUI -or -not (Test-Path $Dist)) {
    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $node) { throw "frontend\dist is missing and Node.js 20.19+ is not installed. Install Node.js LTS or use an export that includes frontend\dist." }
    Push-Location $Frontend
    corepack enable
    yarn install --frozen-lockfile
    yarn build
    Pop-Location
}

$ffprobe = Get-Command ffprobe -ErrorAction SilentlyContinue
if (-not $ffprobe -and -not (Test-Path (Join-Path $Root "tools\ffprobe.exe"))) {
    Write-Host "NOTE: ffprobe not found. Playback works, but codec inspection is disabled. See README > FFprobe." -ForegroundColor DarkYellow
}
Write-Host "Setup complete. Run scripts\windows\start.bat" -ForegroundColor Green
