@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  py -3 local_server.py
) else (
  python local_server.py
)
pause
