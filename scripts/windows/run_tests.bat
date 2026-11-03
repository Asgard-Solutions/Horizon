@echo off
rem Runs the automated backend test suite and the frontend type check.
set ROOT=%~dp0..\..
pushd "%ROOT%\backend"
".venv\Scripts\python.exe" -m pytest -v
set RESULT=%ERRORLEVEL%
popd
if exist "%ROOT%\frontend\node_modules" (
  pushd "%ROOT%\frontend"
  call yarn typecheck
  popd
)
exit /b %RESULT%
