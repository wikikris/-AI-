@echo off
cd /d "%~dp0"
echo Building FuturesPA.exe...
pyinstaller --name=FuturesPA --onefile --console ^
  --add-data="frontend/dist;frontend/dist" ^
  --add-data="config.example.yaml;." ^
  --collect-data=akshare ^
  launcher.py
echo.
echo Done! Output: dist\FuturesPA.exe
pause
