@echo off
title OmniRoute AI Gateway (375+ Providers)
color 0B
cls

echo ===============================================================================
echo                   OmniRoute Local AI Gateway & Router
echo         Unified Endpoint for 375+ Providers (150+ Free) & 1,400+ Models
echo ===============================================================================
echo.
echo [1/2] Launching OmniRoute on http://localhost:20128...
echo [Dashboard] http://localhost:20128/dashboard
echo [API Base]  http://localhost:20128/v1
echo.

where npx >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js / npx is not found in your system PATH.
    echo Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)

echo Starting OmniRoute... (First-time download may take a moment)
echo Once started, manage providers in your browser at http://localhost:20128/dashboard
echo.

npx -y omniroute

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [OmniRoute] Process exited with code %ERRORLEVEL%.
    pause
)
