#!/bin/bash
# Launch .NET Backend and Frontend together
# This script starts both the .NET backend API and the React frontend

echo "========================================"
echo "Starting .NET Agent Framework Workshop"
echo "========================================"

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Start the .NET backend in the background
echo "Starting .NET Backend..."
cd "$SCRIPT_DIR/Backend/dotnet"
dotnet run &
BACKEND_PID=$!

# Wait a moment for the backend to initialize
sleep 3

# Start the frontend in the background
echo "Starting Frontend..."
cd "$SCRIPT_DIR/frontend"
npm start &
FRONTEND_PID=$!

echo "========================================"
echo "Both services are starting..."
echo "- Backend: http://localhost:5000 (or configured port)"
echo "- Frontend: http://localhost:3001"
echo "========================================"
echo "Press Ctrl+C to stop both services."

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Stopping services..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup SIGINT SIGTERM

# Wait for both processes
wait
