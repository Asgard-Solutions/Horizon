@echo off
rem Starts the local media server and opens the UI. Close this window to stop the server.
set ROOT=%~dp0..\..
if not exist "%ROOT%\backend\.venv\Scripts\python.exe" (
  echo Run scripts\windows\setup.bat first.
  pause
  exit /b 1
)
if "%MC_PORT%"=="" set MC_PORT=8765
start "" "http://127.0.0.1:%MC_PORT%/"
"%ROOT%\backend\.venv\Scripts\python.exe" "%ROOT%\backend\run.py" --port %MC_PORT%
pause
