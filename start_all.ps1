# Script to start both Ollama and SecureSphere backend
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SecureSphere Startup Script" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Start Ollama
Write-Host "[1/2] Starting Ollama..." -ForegroundColor Yellow
& "$PSScriptRoot\start_ollama.ps1"

Write-Host ""
Start-Sleep -Seconds 2

# Step 2: Start Backend Server
Write-Host "[2/2] Starting SecureSphere Backend..." -ForegroundColor Yellow
Write-Host ""

Set-Location "$PSScriptRoot\backend"

if (Test-Path "venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\Activate.ps1
    Write-Host "Virtual environment activated" -ForegroundColor Cyan
} else {
    Write-Host "[ERROR] Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please create it first: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Starting server on http://localhost:8000" -ForegroundColor Green
Write-Host "API Docs: http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python start.py
