@echo off
setlocal
cd /d "%~dp0"
echo -----------------------------------------------
echo       PixelStudy Windows EXE Builder
echo -----------------------------------------------
where py >nul 2>nul
if errorlevel 1 goto no_python

py -m pip install -r requirements.txt
if errorlevel 1 goto failed

py -m pip install pyinstaller
if errorlevel 1 goto failed

py -m PyInstaller --noconfirm --clean --onefile --windowed --name PixelStudy --icon "assets\icon.ico" --add-data "assets;assets" "main.py"
if errorlevel 1 goto failed

echo.
echo SUCCESS! Your EXE is in dist\PixelStudy.exe
pause
exit /b 0

:no_python
echo Python Launcher is missing. Install Python from python.org.
pause
exit /b 1

:failed
echo.
echo Build failed. Check the error above.
pause
exit /b 1
