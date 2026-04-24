# Script to start Ollama service
Write-Host "Starting Ollama..." -ForegroundColor Green

# Try to find Ollama executable
$ollamaPaths = @(
    "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
    "$env:ProgramFiles\Ollama\ollama.exe",
    "C:\Program Files\Ollama\ollama.exe",
    "C:\Users\$env:USERNAME\AppData\Local\Programs\Ollama\ollama.exe"
)

$ollamaExe = $null
foreach ($path in $ollamaPaths) {
    if (Test-Path $path) {
        $ollamaExe = $path
        Write-Host "Found Ollama at: $ollamaExe" -ForegroundColor Cyan
        break
    }
}

if (-not $ollamaExe) {
    Write-Host "Ollama executable not found in common locations." -ForegroundColor Yellow
    Write-Host "Please start Ollama manually or add it to your PATH." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To start Ollama manually:" -ForegroundColor Cyan
    Write-Host "1. Open a new terminal" -ForegroundColor White
    Write-Host "2. Run: ollama serve" -ForegroundColor White
    exit 1
}

# Check if Ollama is already running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
    Write-Host "[OK] Ollama is already running!" -ForegroundColor Green
    exit 0
} catch {
    Write-Host "Ollama is not running. Starting it..." -ForegroundColor Yellow
}

# Start Ollama in background
Write-Host "Starting Ollama service..." -ForegroundColor Cyan
Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Minimized

# Wait a bit for it to start
Start-Sleep -Seconds 3

# Check if it started successfully
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "[OK] Ollama started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Checking for required models..." -ForegroundColor Cyan
    
    # Check for llama3
    try {
        $models = (Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2).Content | ConvertFrom-Json
        $modelNames = $models.models | ForEach-Object { $_.name }
        
        if ($modelNames -contains "llama3") {
            Write-Host "[OK] llama3 model found" -ForegroundColor Green
        } else {
            Write-Host "[!] llama3 model not found. Pull it with: ollama pull llama3" -ForegroundColor Yellow
        }
        
        if ($modelNames -contains "nomic-embed-text") {
            Write-Host "[OK] nomic-embed-text model found" -ForegroundColor Green
        } else {
            Write-Host "[!] nomic-embed-text model not found. Pull it with: ollama pull nomic-embed-text" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[!] Could not check models" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "[!] Ollama may still be starting. Wait a few seconds and try again." -ForegroundColor Yellow
    Write-Host "   Or start it manually in a new terminal: ollama serve" -ForegroundColor Cyan
}
