@echo off
REM Luna JARVIS - Quick Start Script
REM Starts both Python service and Electron overlay

echo.
echo  🌙 Luna JARVIS - Starting...
echo  ================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python not found. Please install Python 3.11+
    pause
    exit /b 1
)

REM Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

REM Check MIMO_API_KEY
if "%MIMO_API_KEY%"=="" (
    echo ⚠️  MIMO_API_KEY not set. Set it before running:
    echo     set MIMO_API_KEY=your_key_here
    echo.
)

REM Install Python dependencies
echo 📦 Installing Python dependencies...
cd /d "%~dp0python-service"
pip install -r requirements.txt -q 2>nul

REM Start Python service in background
echo 🚀 Starting Python service on port 8765...
start "Luna JARVIS Service" cmd /c "python main.py"

REM Wait for service to be ready (retry up to 10 times)
echo ⏳ Waiting for service...
set RETRY=0
:WAIT_LOOP
set /a RETRY+=1
timeout /t 3 /nobreak >nul
curl -s http://127.0.0.1:8765/health >nul 2>&1
if not errorlevel 1 (
    echo ✅ Python service is running!
    goto :SERVICE_READY
)
if %RETRY% LSS 10 (
    echo ⏳ Attempt %RETRY%/10 - service not ready yet...
    goto :WAIT_LOOP
)
echo ❌ Service failed to start after 30s. Check the service window.
pause
exit /b 1
:SERVICE_READY

REM Install Electron dependencies
echo 📦 Installing Electron dependencies...
cd /d "%~dp0electron-app"
call npm install -q 2>nul

REM Start Electron
echo 🚀 Starting Electron overlay...
cd /d "%~dp0electron-app"
call npm start

echo.
echo 🌙 Luna JARVIS stopped.
pause
