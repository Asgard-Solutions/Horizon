@echo off
setlocal
rem Open Media Center - start script. Checks dependencies, initialises the SQLite database, then starts the server.
rem Close this window (or press Ctrl+C) to stop.
set "ROOT=%~dp0..\.."
set "PY=%ROOT%\backend\.venv\Scripts\python.exe"
if "%MC_PORT%"=="" set "MC_PORT=8765"

if not exist "%PY%" (
  echo [FAIL] Python environment not found. Run Setup.bat first.
  pause
  exit /b 1
)

"%PY%" "%ROOT%\backend\run.py" --check --port %MC_PORT%
if errorlevel 1 (
  echo.
  echo Startup checks failed. Fix the items marked FAIL above, see docs\WINDOWS_TESTING.md.
  pause
  exit /b 1
)
echo.
"%PY%" "%ROOT%\backend\run.py" --port %MC_PORT% --open-browser
echo Server stopped.
pause
