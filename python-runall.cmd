@echo off
REM Launch Python Backend and Frontend together
REM This script starts both the Python backend API and the React frontend

echo ========================================
echo Starting Python Agent Framework Workshop
echo ========================================

REM Start the Python backend in a new window (with .venv activated)
echo Starting Python Backend...
start "Python Backend" cmd /k "cd /d %~dp0Backend\python && .venv\Scripts\activate && python main.py"

REM Wait a moment for the backend to initialize
timeout /t 3 /nobreak > nul

REM Start the frontend in a new window
echo Starting Frontend...
start "Frontend" cmd /k "cd /d %~dp0frontend && npm start"

echo ========================================
echo Both services are starting...
echo - Backend: http://localhost:8000 (or configured port)
echo - Frontend: http://localhost:3001
echo ========================================
echo Close the opened terminal windows to stop the services.
