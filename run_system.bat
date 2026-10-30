@echo off
title Enterprise Knowledge Copilot
echo ========================================================
echo Launching Enterprise Knowledge Copilot Platform
echo ========================================================
echo.
echo 1. Starting FastAPI Backend on http://127.0.0.1:8000 ...
start "Enterprise Copilot - Backend" "%~dp0run_backend.bat"

echo 2. Starting Next.js Frontend on http://localhost:3000 ...
start "Enterprise Copilot - Frontend" "%~dp0run_frontend.bat"

echo.
echo Both services are launching in dedicated terminal windows:
echo - Frontend: http://localhost:3000
echo - Backend:  http://127.0.0.1:8000
echo - API Docs: http://127.0.0.1:8000/docs
echo.
