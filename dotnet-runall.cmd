@echo off
REM Launch .NET Backend and Frontend together
REM This script starts both the .NET backend API and the React frontend

echo ========================================
echo Starting .NET Agent Framework Workshop
echo ========================================

REM Start the .NET backend in a new window
echo Starting .NET Backend...
start "DotNet Backend" cmd /k "cd /d %~dp0Backend\dotnet && dotnet run"

REM Wait a moment for the backend to initialize
timeout /t 3 /nobreak > nul

REM Start the frontend in a new window
echo Starting Frontend...
start "Frontend" cmd /k "cd /d %~dp0frontend && npm start"

echo ========================================
echo Both services are starting...
echo - Backend: http://localhost:5000 (or configured port)
echo - Frontend: http://localhost:3001
echo ========================================
echo Close the opened terminal windows to stop the services.
