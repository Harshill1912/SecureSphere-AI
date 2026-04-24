@echo off
echo Starting SecureSphere Backend Server...
echo.

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Check if activation was successful
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    echo Please make sure you have created the virtual environment
    pause
    exit /b 1
)

REM Start the server
echo Starting server on http://localhost:8000
echo Press Ctrl+C to stop the server
echo.
python start.py

pause
