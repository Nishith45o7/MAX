@echo off
title MAX Telegram Gateway Bot
color 0B
cls

echo ===============================================================================
echo                MAX Mobile Gateway - Telegram Bot Daemon
echo ===============================================================================
echo.
echo Starting MAX Telegram Bot (@maxiummbot)...
echo You can talk to MAX from your phone on Telegram!
echo.

python -m gateway.telegram_gateway

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Bot exited with error code %ERRORLEVEL%.
    pause
)
