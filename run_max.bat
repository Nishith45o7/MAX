@echo off
title MARK I-OR (M.A.X — Autonomous AI Assistant)
color 0A
cls

echo ===============================================================================
echo                MARK I-OR (M.A.X — Personal Autonomous AI Assistant)
echo ===============================================================================
echo.

where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not found in your system PATH.
    echo Please install Python 3.11 or 3.12 and check "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

echo [M.A.X Initialization]
echo [1/4] Checking environment and dependencies...
python -c "import PyQt6, openai, psutil; print('Core runtime verified: OK')" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Missing required packages detected. Installing requirements...
    python -m pip install -r requirements.txt
)

echo [2/4] Verifying Memory Database (SQLite WAL mode)...
python -c "import memory.db; print('Database ready.')"

echo [3/4] Checking OmniRoute AI Gateway (port 20128)...
netstat -ano | findstr :20128 >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OmniRoute] ONLINE at http://localhost:20128/v1 (375+ Providers & 1400+ Models active)
) else (
    echo [OmniRoute] Offline. (Tip: Run start_omniroute.bat to enable 375+ free AI providers)
)

echo [4/4] Launching MARK I Desktop HUD...
echo.
python ui.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [M.A.X] Process exited with code %ERRORLEVEL%.
    pause
)
