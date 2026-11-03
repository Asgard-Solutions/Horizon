@echo off
setlocal
rem Runs the automated backend test suite (offline) and, if Node.js modules are installed, the frontend type check.
set "ROOT=%~dp0..\.."
set "PY=%ROOT%\backend\.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo Run Setup.bat first.
  exit /b 1
)
pushd "%ROOT%\backend"
"%PY%" -m pytest -v -n 0 --junitxml="%ROOT%\test-results-windows.xml"
set RESULT=%ERRORLEVEL%
popd
if exist "%ROOT%\frontend\node_modules" (
  pushd "%ROOT%\frontend"
  call yarn typecheck
  popd
)
echo.
if %RESULT%==0 (echo Backend tests PASSED. Results: test-results-windows.xml) else (echo Backend tests FAILED - see output above.)
exit /b %RESULT%
