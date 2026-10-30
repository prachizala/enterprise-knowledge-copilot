@echo off
title Enterprise Knowledge Copilot - Frontend
echo ===================================================
echo Starting Next.js Frontend on http://localhost:3000
echo ===================================================
cd /d "%~dp0frontend"
npm run dev
pause
