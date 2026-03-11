@echo off
echo [%date% %time%] Starting daily cat video generation... >> "%~dp0logs\daily.log"

cd /d "%~dp0"

"C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe" agent.py generate --upload --privacy public >> "%~dp0logs\daily.log" 2>&1

echo [%date% %time%] Done. >> "%~dp0logs\daily.log"
echo. >> "%~dp0logs\daily.log"
