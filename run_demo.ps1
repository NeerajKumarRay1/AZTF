# AI-NGFW Demo Launcher (Windows, dry-run mode)
# Runs the FastAPI API + dashboard. No models/datasets/WSL needed.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== AI-NGFW Demo ===" -ForegroundColor Cyan

# 1. Install minimal demo dependencies
Write-Host "Installing demo dependencies..." -ForegroundColor Yellow
python -m pip install --quiet fastapi "uvicorn[standard]" pyjwt bcrypt python-dotenv psutil websockets

# 2. Init DB + seed users (admin/analyst/viewer, pw: password123)
Write-Host "Initializing database and seeding users..." -ForegroundColor Yellow
python -c "import zero_trust; print('Users seeded.')"

# 3. Launch API server
Write-Host "Starting API on http://localhost:8000" -ForegroundColor Green
Write-Host "Dashboard: http://localhost:8000/dashboard/index.html" -ForegroundColor Green
Write-Host "Login -> admin / password123" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop." -ForegroundColor DarkGray
python -m uvicorn app:app --host 0.0.0.0 --port 8000
