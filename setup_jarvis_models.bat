@echo off
setlocal EnableDelayedExpansion
color 0B
echo.
echo =======================================================
echo     JARVIS AI Assistant - Setup ^& Model Installer
echo =======================================================
echo.

:: ── Step 1: Install Ollama from local exe if not already installed ───────────
set "OLLAMA_EXE="

:: Check if already on PATH
where ollama >nul 2>&1
if %errorlevel%==0 (
    set "OLLAMA_EXE=ollama"
    echo [1/4] Ollama already on PATH.
    goto :check_local_dirs
)

:check_local_dirs
:: Check common install locations
for %%P in (
    "%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
    "%PROGRAMFILES%\Ollama\ollama.exe"
    "%USERPROFILE%\AppData\Local\Programs\Ollama\ollama.exe"
) do (
    if exist %%P (
        set "OLLAMA_EXE=%%~P"
        echo [1/4] Ollama found at: %%~P
        goto :start_server
    )
)

:: Not found anywhere - install from local OllamaSetup.exe
if exist "%~dp0OllamaSetup.exe" (
    echo [1/4] Installing Ollama from local OllamaSetup.exe...
    start /wait "" "%~dp0OllamaSetup.exe" /SP- /VERYSILENT /NORESTART
    echo     Installation complete.
    timeout /t 6 /nobreak >nul
) else (
    echo.
    echo  ERROR: OllamaSetup.exe not found in this folder.
    echo  Please place OllamaSetup.exe in the same folder as this script.
    pause
    exit /b 1
)

:: Refresh PATH for this session
set "PATH=%LOCALAPPDATA%\Programs\Ollama;%PATH%"

:: Re-check after install
for %%P in (
    "ollama"
    "%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
    "%PROGRAMFILES%\Ollama\ollama.exe"
    "%USERPROFILE%\AppData\Local\Programs\Ollama\ollama.exe"
) do (
    if exist "%%~P" (
        set "OLLAMA_EXE=%%~P"
        goto :start_server
    )
)
where ollama >nul 2>&1
if %errorlevel%==0 (
    set "OLLAMA_EXE=ollama"
    goto :start_server
)

echo.
echo  ERROR: Ollama installed but still not found.
echo  Please close this window, open a NEW terminal, and run this script again.
pause
exit /b 1

:: ── Step 2: Start Ollama server ──────────────────────────────────────────────
:start_server
echo.
echo [2/4] Starting Ollama server...
start /b "" !OLLAMA_EXE! serve >nul 2>&1
timeout /t 5 /nobreak >nul
echo     Server started.

:: ── Step 3: Pull Mistral 7B ──────────────────────────────────────────────────
echo.
echo =======================================================
echo [3/4] Downloading Mistral 7B  (~4.1 GB)
echo       Text + command engine - please wait...
echo =======================================================
echo.
!OLLAMA_EXE! pull mistral:7b
if %errorlevel% neq 0 (
    echo  Retrying Mistral download...
    timeout /t 3 /nobreak >nul
    !OLLAMA_EXE! pull mistral:7b
)

:: ── Step 4: Pull LLaVa ───────────────────────────────────────────────────────
echo.
echo =======================================================
echo [4/4] Downloading LLaVa  (~4.5 GB)
echo       Screen vision engine - please wait...
echo =======================================================
echo.
!OLLAMA_EXE! pull llava
if %errorlevel% neq 0 (
    echo  Retrying LLaVa download...
    timeout /t 3 /nobreak >nul
    !OLLAMA_EXE! pull llava
)

:: ── Step 5: Python dependencies ──────────────────────────────────────────────
echo.
echo =======================================================
echo  Installing Python packages...
echo =======================================================
python -m pip install --upgrade pip --quiet
python -m pip install -r "%~dp0requirements.txt"

:: ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo =======================================================
echo  ALL DONE! JARVIS is ready.
echo.
echo  Run JARVIS:
echo    python run.py
echo.
echo  Flags:
echo    --debug       verbose logging
echo    --no-voice    skip TTS greeting
echo    --auto-play   start game AI immediately
echo =======================================================
echo.
pause
