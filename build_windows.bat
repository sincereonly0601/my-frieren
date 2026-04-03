@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [1/2] Installing runtime + build dependencies...
python -m pip install -r requirements.txt -r requirements-build.txt
if errorlevel 1 exit /b 1

echo [2/2] PyInstaller (onedir) ...
pyinstaller --noconfirm build_windows.spec
if errorlevel 1 exit /b 1

echo.
echo OK: dist\葬送的魔法使夢工廠\葬送的魔法使夢工廠.exe
echo Zip the whole folder "葬送的魔法使夢工廠" (exe + _internal) for other PCs.
pause
