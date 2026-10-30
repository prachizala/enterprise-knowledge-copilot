# Enterprise Knowledge Copilot PowerShell Launcher
$rootDir = $PSScriptRoot

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Launching Enterprise Knowledge Copilot Platform" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan

# Start Backend
Write-Host "Starting Backend on http://127.0.0.1:8000 ..." -ForegroundColor Green
Start-Process wt -ArgumentList "-w 0 nt -d `"$rootDir\backend`" powershell -NoExit -Command `"Write-Host 'FastAPI Backend Running on http://127.0.0.1:8000' -ForegroundColor Green; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`"" -ErrorAction SilentlyContinue

# Fallback to cmd if wt (Windows Terminal) is not default
if ($LASTEXITCODE -ne 0) {
    Start-Process cmd -ArgumentList "/k cd /d `"$rootDir\backend`" && .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
}

# Start Frontend
Write-Host "Starting Frontend on http://localhost:3000 ..." -ForegroundColor Green
Start-Process cmd -ArgumentList "/k cd /d `"$rootDir\frontend`" && npm run dev"

Write-Host ""
Write-Host "Servers launched:" -ForegroundColor Yellow
Write-Host "- Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "- Backend:  http://127.0.0.1:8000" -ForegroundColor White
Write-Host "- Swagger:  http://127.0.0.1:8000/docs" -ForegroundColor White
