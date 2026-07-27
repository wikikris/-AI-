@echo off
cd /d "%~dp0"
echo Killing existing server...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
timeout /t 1 /nobreak >nul
echo Starting server...
start http://localhost:8000
C:\Users\zard\miniconda3\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
