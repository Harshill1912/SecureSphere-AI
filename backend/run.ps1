# PowerShell script to start SecureSphere Backend
Write-Host "Starting SecureSphere Backend Server..." -ForegroundColor Green
Write-Host ""

# Navigate to backend directory
Set-Location $PSScriptRoot

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\Activate.ps1
} else {
    Write-Host "ERROR: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please create it with: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

# Check if Python is available
try {
    $pythonVersion = python --version
    Write-Host "Python: $pythonVersion" -ForegroundColor Cyan
} catch {
    Write-Host "ERROR: Python not found in PATH!" -ForegroundColor Red
    exit 1
}

# Start the server
Write-Host ""
Write-Host "Starting server on http://localhost:8000" -ForegroundColor Green
Write-Host "API Docs: http://localhost:8000/api/docs" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

python start.py
