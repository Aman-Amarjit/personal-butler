@echo off
title PANDA AI Assistant
echo ==========================================
echo   PANDA AI Assistant - Starting...
echo ==========================================
echo.

REM Always run from the directory where this .bat lives
cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Activate venv if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo No virtual environment found, using system Python.
    echo Tip: create one with:  python -m venv venv
)

REM Install/update dependencies quietly
echo Checking dependencies...
pip install -r requirements.txt -q --disable-pip-version-check
if errorlevel 1 (
    echo WARNING: Some dependencies may not have installed correctly.
)

REM Set environment to production
set PANDA_ENV=production

echo.
echo Starting PANDA AI Assistant...
echo Say "Hey PANDA" to activate voice commands.
echo Press ESC in the overlay window to quit.
echo.

python run.py %*

echo.
echo PANDA has exited.
pause
