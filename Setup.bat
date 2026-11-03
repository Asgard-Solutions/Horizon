@echo off
rem One-time installation. Works offline when vendor\wheels is present (included in the release zip).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\windows\setup.ps1" %*
pause
