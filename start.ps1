# Luna JARVIS - Quick Start Script (PowerShell)
# Starts both Python service and Electron overlay

Write-Host ""
Write-Host "  🌙 Luna JARVIS - Starting..." -ForegroundColor Magenta
Write-Host "  ================================" -ForegroundColor DarkGray
Write-Host ""

$projectRoot = $PSScriptRoot

# Check Python
try {
    $pyVersion = python --version 2>&1
    Write-Host "  ✅ Python: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Check Node
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  ✅ Node.js: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

# Check MIMO_API_KEY
if (-not $env:MIMO_API_KEY) {
    Write-Host "  ⚠️  MIMO_API_KEY not set. Set it before running:" -ForegroundColor Yellow
    Write-Host "      `$env:MIMO_API_KEY = 'your_key_here'" -ForegroundColor DarkYellow
    Write-Host ""
}

# Install Python dependencies
Write-Host "  📦 Installing Python dependencies..." -ForegroundColor Cyan
Push-Location "$projectRoot\python-service"
pip install -r requirements.txt -q 2>$null
Pop-Location

# Start Python service in background
Write-Host "  🚀 Starting Python service on port 8765..." -ForegroundColor Cyan
$serviceJob = Start-Job -ScriptBlock {
    Set-Location "$using:projectRoot\python-service"
    python main.py
}

# Wait for service to be ready
Write-Host "  ⏳ Waiting for service..." -ForegroundColor DarkGray
Start-Sleep -Seconds 3

# Check if service is running
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8765/health" -TimeoutSec 5
    Write-Host "  ✅ Python service is running! Mode: $($health.mode.mode)" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Service might not be ready yet. Check with: Receive-Job $($serviceJob.Id)" -ForegroundColor Yellow
}

# Install Electron dependencies
Write-Host "  📦 Installing Electron dependencies..." -ForegroundColor Cyan
Push-Location "$projectRoot\electron-app"
npm install -q 2>$null
Pop-Location

# Start Electron
Write-Host "  🚀 Starting Electron overlay..." -ForegroundColor Cyan
Write-Host "  💡 Press Alt+L to toggle overlay" -ForegroundColor DarkGray
Write-Host ""

Push-Location "$projectRoot\electron-app"
npm start

# Cleanup
Write-Host ""
Write-Host "  🌙 Luna JARVIS stopped." -ForegroundColor Magenta
Stop-Job $serviceJob -ErrorAction SilentlyContinue
Remove-Job $serviceJob -ErrorAction SilentlyContinue
Pop-Location
