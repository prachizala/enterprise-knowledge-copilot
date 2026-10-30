@echo off
title Enterprise Knowledge Copilot - Backend
echo ===================================================
echo Starting FastAPI Backend on http://127.0.0.1:8000
echo API Docs: http://127.0.0.1:8000/docs
echo ===================================================
cd /d "%~dp0backend"
.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
pause
