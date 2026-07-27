@echo off
cd /d "%~dp0"
start http://localhost:8000
C:\Users\zard\miniconda3\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
pause
